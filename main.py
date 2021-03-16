from tkinter import *
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
from PIL import Image, ImageTk
import json
import os
import glob
import random
import time

import numpy as np

COLORS = ['red', 'lawn green', 'pink', 'cyan', 'blue', 'black']
# image sizes for the examples
SIZE = 256, 256


class PoseLabelTool():
    def __init__(self, master):
        # set up the main frame
        self.parent = master
        self.parent.title('PoseLabelTool')
        self.frame = Frame(self.parent)
        self.frame.pack(fill=BOTH, expand=True)
        self.parent.resizable(width=FALSE, height=FALSE)

        # initialize global state
        self.img = None
        self.imageDir = ''
        self.imageList = []
        self.egDir = ''
        self.egList = []
        self.labelDir = ''
        self.jsonDir = ''
        self.cur = 0
        self.total = 0
        # self.category = 0
        self.imagename = ''
        self.labelfilename = ''
        self.jsonfilename = ''
        self.tkimg = None
        self.currentLabelclass = ''
        self.cla_can_temp = []
        self.jointenumfilename = 'joint_enum.txt'
        self.jointmapping = [0, 1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 8]
        self.jointconnections = [
            [0, 1], [1, 2], [2, 3], [3, 4],
            [1, 5], [5, 6], [6, 7],
            [1, 14], [14, 8], [8, 9], [9, 10],
            [14, 11], [11, 12], [12, 13]
        ]
        self.r = 8

        # initialize mouse state
        self.STATE = {}
        self.STATE['add'] = 0
        self.STATE['click'] = 0
        self.STATE['x'], self.STATE['y'] = 0, 0

        # List of people
        # Initialize when loading image
        self.personIdsList = []  # Expected to be an 2D list
        self.personList = []     # List to reference people
        # Person representing variables
        # Initialize when any modification happens
        self.personIds = None      # List of IDs of circles and lines
        self.joints = None
        self.personColor = None
        self.personIdx = None
        self.jointIdx = None
        self.hl = None
        self.vl = None

        # ----------------- GUI stuff ---------------------
        # dir entry & load
        # input image dir button
        self.srcDirBtn = Button(self.frame, text='Input image folder', command=self.selectSrcDir)
        self.srcDirBtn.grid(row=0, column=0, sticky=W+E)
        
        # input image dir entry
        self.svSourcePath = StringVar()
        self.entrySrc = Entry(self.frame, textvariable=self.svSourcePath)
        self.entrySrc.grid(row=0, column=1, sticky=W+E)
        # self.svSourcePath.set(os.path.join(os.getcwd(), 'images/samples'))
        self.svSourcePath.set(
            'E:\\Datasets\\SIAT\\SIAT_DB_v2\\samples\\images\\danger'
        )

        # label file save dir button
        self.desDirBtn = Button(self.frame, text='Output label folder',
                                command=self.selectDesDir)
        self.desDirBtn.grid(row=1, column=0, sticky=W + E)

        # label file save dir entry
        self.svDestinationPath = StringVar()
        self.entryDes = Entry(self.frame, textvariable=self.svDestinationPath)
        self.entryDes.grid(row=1, column=1, sticky=W+E)
        # self.svDestinationPath.set(os.path.join(os.getcwd(), 'labels/samples'))
        self.svDestinationPath.set(
            'E:\\Datasets\\SIAT\\SIAT_DB_v2\\samples\\labels\\pose\\danger'
        )

        # load button
        self.ldBtn = Button(self.frame, text='Load Dir', command=self.loadDir)
        self.ldBtn.grid(row=0, column=2, rowspan=2, columnspan=2)

        # main panel for labeling
        self.mainPanel = Canvas(self.frame, cursor='tcross')
        self.mainPanel.bind('<Button-1>', self.mouseClick)
        self.mainPanel.bind('<Motion>', self.mouseMove)
        self.parent.bind('<Escape>', self.cancelClick)

        # Shortcuts
        self.parent.bind('a', self.prevImage)  # press 'a' to go backward
        self.parent.bind('d', self.nextImage)  # press 'd' to go forward
        self.parent.bind('x', self.delPersonShortcut)
        self.parent.bind('c', self.addPersonShortcut)
        # self.parent.bind('Shift-s', self.cancelJoint)
        self.parent.bind('<Control-s>', self.cancelPerson)
        self.parent.bind('<Control-a>', self.prevJoint)
        self.parent.bind('<Control-d>', self.nextJoint)
        self.mainPanel.grid(row=2, column=1, rowspan=4, sticky=W+N)

        # choose class
        self.classname = StringVar()
        self.classcandidate = ttk.Combobox(self.frame, state='readonly', textvariable=self.classname)
        self.classcandidate.grid(row=2, column=2, columnspan=2, sticky=W+E)
        if os.path.exists(self.jointenumfilename):
            with open(self.jointenumfilename) as cf:
                for line in cf.readlines():
                    self.cla_can_temp.append(line.strip('\n'))
        self.classcandidate['values'] = self.cla_can_temp
        self.classcandidate.current(0)
        self.currentLabelclass = self.classcandidate.get()
        self.classcandidate.bind('<<ComboboxSelected>>', self.setClass)
        self.numJoints = len(self.cla_can_temp)
        # self.btnclass = Button(self.frame, text='ComfirmClass', command=self.setClass)
        # self.btnclass.grid(row=2, column=3, sticky=W+E)

        # showing bbox info & delete bbox
        self.lb1 = Label(self.frame, text='Annotated People:')
        self.lb1.grid(row=3, column=2, sticky=W+N)
        self.listbox = Listbox(self.frame, width=22, height=12)
        self.listbox.grid(row=4, column=2, rowspan=2, sticky=N+S)
        self.listbox.bind('<Button-3>', self.clearSelection)
        self.btnAdd = Button(self.frame, text='Add', command=self.addPerson)
        self.btnAdd.grid(row=4, column=3, sticky=W+E+N)
        self.btnDel = Button(self.frame, text='Delete', command=self.delPerson)
        self.btnDel.grid(row=4, column=3, sticky=W+E+S)
        self.btnClear = Button(self.frame, text='ClearAll', command=self.clearPerson)
        self.btnClear.grid(row=5, column=3)

        # control panel for image navigation
        self.ctrPanel = Frame(self.frame)
        self.ctrPanel.grid(row=6, column=0, columnspan=3, sticky=W+E)
        self.prevBtn = Button(self.ctrPanel, text='<< Prev', width=10, command=self.prevImage)
        self.prevBtn.pack(side=LEFT, padx=5, pady=3)
        self.nextBtn = Button(self.ctrPanel, text='Next >>', width=10, command=self.nextImage)
        self.nextBtn.pack(side=LEFT, padx=5, pady=3)
        self.progLabel = Label(self.ctrPanel, text='Progress:     /    ')
        self.progLabel.pack(side=LEFT, padx=5)
        self.tmpLabel = Label(self.ctrPanel, text='Go to Image No.')
        self.tmpLabel.pack(side=LEFT, padx=5)
        self.idxEntry = Entry(self.ctrPanel, width=5)
        self.idxEntry.pack(side=LEFT)
        self.goBtn = Button(self.ctrPanel, text='Go', command=self.gotoImage)
        self.goBtn.pack(side=LEFT)

        # example pannel for illustration
        self.egPanel = Frame(self.frame, border=10)
        self.egPanel.grid(row=2, column=0, rowspan=4, sticky=N)
        self.egLabelTitle = Label(self.egPanel, text='Joint Enumeration')
        self.egLabelImage = Label(self.egPanel)
        self.egCurrentJoint = Label(self.egPanel, text='Current Joint:')

        self.egLabelTitle.pack(side=TOP, pady=5)
        self.egLabelImage.pack(side=TOP, pady=5)
        self.egCurrentJoint.pack(side=BOTTOM, pady=5)


        # self.tmpLabel2.pack(side=TOP, pady=5)
        # self.egLabels = []
        # for i in range(3):
        #     self.egLabels.append(Label(self.egPanel))
        #     self.egLabels[-1].pack(side=TOP)

        # display mouse position
        self.disp = Label(self.ctrPanel, text='')
        self.disp.pack(side=RIGHT)

        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(4, weight=1)

        self.radius = 4

    def selectSrcDir(self):
        path = filedialog.askdirectory(title='Select image source folder', initialdir=self.svSourcePath.get())
        self.svSourcePath.set(path)

    def selectDesDir(self):
        path = filedialog.askdirectory(title='Select label output folder', initialdir=self.svDestinationPath.get())
        self.svDestinationPath.set(path)
    
    def loadDir(self):
        self.parent.focus()
        # get image list
        # self.imageDir = os.path.join(r'./Images', '%03d' %(self.category))
        self.imageDir = self.svSourcePath.get()
        if not os.path.isdir(self.imageDir):
            messagebox.showerror('Error!', message='The specified dir does not exist!')
            return
        
        extlist = ['*.jpg', '*.png', '*.bmp']
        for e in extlist:
            filelist = glob.glob(os.path.join(self.imageDir, e))
            self.imageList.extend(filelist)
        # self.imageList = glob.glob(os.path.join(self.imageDir, '*.JPEG'))
        if len(self.imageList) == 0:
            print('No .jpg images found in the specified dir!')
            return
        
        # default to the 1st image in the collection
        self.cur = 1
        self.total = len(self.imageList)
        print(self.imageList)
        # set up output dir
        # self.labelDir = os.path.join(r'./Labels', '%03d' %(self.category))
        self.labelDir = self.svDestinationPath.get()
        if not os.path.exists(self.labelDir):
            os.mkdir(self.labelDir)
        
        self.jsonDir = self.imageDir.replace('images', 'json')
        
        # Load joint enumeration image
        im = Image.open('./joint_enum.png')
        size = im.size
        factor = max(size[0] / 400, size[1] / 800., 1.)
        im = im.resize(
            (int(size[0] / factor), int(size[1] / factor))
        )
        self.egtkimg = ImageTk.PhotoImage(im)
        width, height = self.egtkimg.width(), self.egtkimg.height()
        self.egLabelImage.config(image=self.egtkimg, width=width, height=height)

        self.loadImage()
        print('%d images loaded from %s' % (self.total, self.imageDir))

    def drawPerson(self, joints, color):
        personIds = {'joints': [], 'bones': []}
        # Draw joints
        for x, y, c in joints:
            if c == 2:
                tmpId = self.mainPanel.create_oval(
                    x - self.r, y - self.r, x + self.r, y + self.r,
                    fill=color, width=0
                )
            elif c == 1:
                tmpId = self.mainPanel.create_rectangle(
                    x - self.r, y - self.r, x + self.r, y + self.r,
                    fill=color
                )
            else:
                continue
            personIds['joints'].append(tmpId)
        # Draw bones
        for p, c in self.jointconnections:
            px, py, pc = joints[p, :]
            cx, cy, cc = joints[c, :]
            if pc * cc > 0:
                tmpId = self.mainPanel.create_line(
                    px, py, cx, cy,
                    fill=color, width=self.r // 2,
                )
                personIds['bones'].append(tmpId)
        return personIds

    def countOcclusions(self, joints):
        count = [0, 0]
        for _, _, c in joints:
            if int(c) == 0:  # Completely invisible
                count[0] = count[0] + 1
            elif int(c) == 1:  # Partially invisible (and inferrable)
                count[1] = count[1] + 1
            else:  # Fully visible
                continue
        return tuple(count)

    def loadImage(self):
        self.STATE = {}
        self.STATE['add'] = 0
        self.STATE['click'] = 0
        self.STATE['x'], self.STATE['y'] = 0, 0

        # List of people
        # Initialize when loading image
        # self.personIdsList = []  # Expected to be an 2D list
        # self.personList = []  # List to reference people
        # Person representing variables
        # Initialize when any modification happens
        # self.personIds = None  # List of IDs of circles and lines
        # self.joints = None
        # self.personColor = None
        # self.personIdx = None
        # self.jointIdx = None
        # self.hl = None
        # self.vl = None
        # load image
        imagepath = self.imageList[self.cur - 1]
        self.img = Image.open(imagepath)
        size = self.img.size
        # self.factor = 1
        self.factor = max(size[0]/1000, size[1]/1000., 1.)
        self.img = self.img.resize((int(size[0]/self.factor), int(size[1]/self.factor)))
        self.tkimg = ImageTk.PhotoImage(self.img)
        width, height = self.tkimg.width(), self.tkimg.height()
        self.mainPanel.config(width=max(width, 400), height=max(height, 400))
        self.mainPanel.create_image(width / 2, height / 2, image=self.tkimg)
        self.progLabel.config(text='%04d/%04d' % (self.cur, self.total))

        # load labels
        self.clearPerson()
        #self.imagename = os.path.split(imagepath)[-1].split('.')[0]
        fullfilename = os.path.basename(imagepath)
        self.imagename, _ = os.path.splitext(fullfilename)
        self.labelfilename = os.path.join(self.labelDir, self.imagename + '.txt')
        self.jsonfilename = os.path.join(self.jsonDir,
                                         self.imagename + '_keypoints.json')
        if os.path.exists(self.labelfilename):
            with open(self.labelfilename) as f:
                for line in f.readlines():
                    joints = np.array([int(x) for x in line.split(',')])
                    joints = np.reshape(joints, (self.numJoints, 3))
                    joints[:, :-1] = joints[:, :-1] / self.factor
                    self.personList.append(joints.astype(int))
        else:
            print(self.jsonfilename)
            with open(self.jsonfilename, 'r') as f:
                for person in json.load(f)['people']:
                    keypoints = person['pose_keypoints_2d']
                    keypoints_npy = np.reshape(np.array(keypoints), (-1, 3))
                    valid = keypoints_npy[:, -1] > 0
                    joints = np.zeros((self.numJoints, 3))
                    for i, j in enumerate(self.jointmapping):
                        if valid[j]:
                            joints[i, :-1] = keypoints_npy[j, :-1] / self.factor
                            joints[i, -1] = 2

                    joints[-1, :-1] = (
                        2 * keypoints_npy[1, :-1] + keypoints_npy[9, :-1] +
                        keypoints_npy[12, :-1]
                    ) / (4 * self.factor)
                    self.personList.append(joints.astype(int))

        # Draw skeleton from labels
        for i, joints in enumerate(self.personList):
            color_index = i % len(COLORS)
            personIds = self.drawPerson(joints, COLORS[color_index])
            self.personIdsList.append(personIds)
            self.listbox.insert(
                END,
                'Person with (%d, %d) occlusions' %
                self.countOcclusions(joints)
            )
            self.listbox.itemconfig(
                len(self.personIdsList) - 1, fg=COLORS[color_index]
            )

    def saveImage(self):
        if self.labelfilename == '':
            return
        with open(self.labelfilename, 'w') as f:
            for joints in self.personList:
                joints_scaled = joints.copy()
                joints_scaled[:, :-1] = joints_scaled[:, :-1] * self.factor
                joints_str = [
                    '%d' % int(x) for x in joints_scaled.flatten()
                ]
                f.write(','.join(joints_str) + '\n')
        print('Image No. %d saved' % self.cur)

    def searchNear(self, x, y, kypt):
        kypt_x, kypt_y = kypt
        range_x = [kypt_x - self.radius, kypt_x + self.radius]
        range_y = [kypt_y - self.radius, kypt_y + self.radius]
        if range_x[0] <= x <= range_x[1] and range_y[0] <= y <= range_y[1]:
            return True
        else:
            return False

    def saveAndRedraw(self):
        self.delPersonIds(self.personIds)
        self.personIdsList.pop(self.personIdx)
        self.personList.pop(self.personIdx)

        self.personIds = self.drawPerson(self.joints, self.personColor)
        self.personIdsList.insert(self.personIdx, self.personIds)
        self.personList.insert(self.personIdx, self.joints)

        self.listbox.delete(self.personIdx)
        self.listbox.insert(
            self.personIdx,
            'Person with (%d, %d) occlusions' %
            self.countOcclusions(self.joints)
        )
        self.listbox.itemconfig(self.personIdx, fg=self.personColor)
        self.listbox.select_set(self.personIdx)
        self.listbox.event_generate("<<ListboxSelect>>")

        self.personIds = []
        self.joints = []
        self.personIdx = None
        self.jointIdx = None
        self.personColor = None

    def mouseClick(self, event):
        if self.STATE['add']:  # If add button is clicked
            self.joints[self.jointIdx, :] = [event.x, event.y, 2]
            if self.personIds:
                self.delPersonIds(self.personIds)
            self.personIds = self.drawPerson(self.joints, self.personColor)
            return

        sel = self.listbox.curselection()
        if not self.STATE['click']:
            if len(sel) == 1:  # If combobox is selected
                self.personIdx = int(sel[0])
                self.personIds = self.personIdsList[self.personIdx]
                self.joints = self.personList[self.personIdx]
                self.jointIdx = self.cla_can_temp.index(self.currentLabelclass)
                self.personColor = self.mainPanel.itemcget(
                    self.personIds['joints'][0], 'fill'
                )
                if self.joints[self.jointIdx, -1] == 0:
                    self.joints[self.jointIdx, :] = [event.x, event.y, 2]
                    self.saveAndRedraw()
                else:
                    isNear = self.searchNear(
                        event.x, event.y, self.joints[self.jointIdx, :-1]
                    )
                    if isNear:
                        print('selected')
                        curJointName = self.cla_can_temp[self.jointIdx]
                        self.egCurrentJoint.config(
                            text='Current Joint: %s' % curJointName
                        )
                        self.STATE['click'] = 1 - self.STATE['click']
                    else:
                        self.personIds = []
                        self.joints = []
                        self.personIdx = None
                        self.jointIdx = None
                        self.personColor = None
        else:
            self.joints[self.jointIdx, :-1] = [event.x, event.y]
            self.saveAndRedraw()
            self.STATE['click'] = 1 - self.STATE['click']

    def mouseMove(self, event):
        self.disp.config(text='x: %d, y: %d' % (event.x, event.y))
        if self.tkimg:
            if self.hl:
                self.mainPanel.delete(self.hl)
            self.hl = self.mainPanel.create_line(0, event.y, self.tkimg.width(), event.y, width=2)
            if self.vl:
                self.mainPanel.delete(self.vl)
            self.vl = self.mainPanel.create_line(event.x, 0, event.x, self.tkimg.height(), width=2)
        if self.STATE['click']:
            if self.STATE['add']:
                return
            if self.personIds:
                self.delPersonIds(self.personIds)
            self.joints[self.jointIdx, :-1] = [event.x, event.y]
            self.personIds = self.drawPerson(self.joints, self.personColor)

    def clearSelection(self, event=None):
        self.listbox.selection_clear(0, END)
        self.STATE['click'] = 0

    def gotoImage(self):
        idx = int(self.idxEntry.get())
        if 1 <= idx and idx <= self.total:
            self.saveImage()
            self.cur = idx
            self.loadImage()

    def prevImage(self, event=None):
        self.saveImage()
        if self.cur > 1:
            self.cur -= 1
            self.loadImage()

    def nextImage(self, event=None):
        self.saveImage()
        if self.cur < self.total:
            self.cur += 1
            self.loadImage()

    def delJoint(self):
        pass

    def prevJoint(self, event=None):
        print('prev joint')
        if self.STATE['add']:
            if self.jointIdx > 0:
                self.jointIdx -= 1
                curJointName = self.cla_can_temp[self.jointIdx]
                self.egCurrentJoint.config(
                    text='Current Joint: %s' % curJointName
                )

    def nextJoint(self, event=None):
        print('next joint')
        if self.STATE['add']:
            if self.jointIdx < self.numJoints:
                self.jointIdx += 1
                if self.jointIdx == self.numJoints:
                    # Add personIds and joints to list
                    self.personIdsList.append(self.personIds)
                    self.personList.append(self.joints)
                    self.listbox.insert(
                        END,
                        'Person with (%d, %d) occlusions' %
                        self.countOcclusions(self.joints)
                    )
                    self.listbox.itemconfig(
                        len(self.personIdsList) - 1, fg=self.personColor
                    )
                    self.egCurrentJoint.config(text='Current Joint:')
                    self.jointIdx = 0
                    self.STATE['add'] = 0
                    self.personIds = []
                    self.joints = []
                else:
                    curJointName = self.cla_can_temp[self.jointIdx]
                    self.egCurrentJoint.config(
                        text='Current Joint: %s' % curJointName
                    )

    def delPersonIds(self, personIds):
        for key in personIds:
            for tmpId in personIds[key]:
                self.mainPanel.delete(tmpId)

    def cancelPerson(self, event):
        if self.STATE['add']:
            self.delPersonIds(self.personIds)
            self.personIds = {}
            self.joints = []
            self.personIdx = None
            self.jointIdx = None
            self.personColor = None
            self.STATE['add'] = 0

    def cancelClick(self, event):
        pass

    def addPersonShortcut(self, event):
        self.addPerson()

    def addPerson(self):
        self.joints = np.zeros([self.numJoints, 3], dtype=int)
        color_index = len(self.personIdsList) % len(COLORS)
        self.jointIdx = 0
        self.personColor = COLORS[color_index]
        # self.personIds = self.drawPerson(self.joints, self.personColor)
        # self.personIdsList.append(personIds)
        # self.listbox.insert(
        #     END,
        #     'Person with (%d, %d) occlusions' %
        #     self.countOcclusions(joints)
        # )
        startJointName = self.cla_can_temp[self.jointIdx]
        self.egCurrentJoint.config(text='Current Joint: %s' % startJointName)
        self.STATE['add'] = 1

    def delPersonShortcut(self, event):
        self.delPerson()

    def delPerson(self):
        sel = self.listbox.curselection()
        if len(sel) != 1:
            return
        idx = int(sel[0])
        personIds = self.personIdsList[idx]
        self.delPersonIds(personIds)
        self.personIdsList.pop(idx)
        self.personList.pop(idx)
        self.listbox.delete(idx)

        # Return to initial state
        self.personIds = {}
        self.joints = []
        self.personIdx = None
        self.jointIdx = None
        self.personColor = None

    def clearPerson(self):
        # Clear every peoople
        self.listbox.delete(0, len(self.personList))
        for idx in range(len(self.personIdsList)):
            personIds = self.personIdsList[idx]
            self.delPersonIds(personIds)
        self.personIdsList = []
        self.personList = []

        # Return to initial state
        self.personIds = []
        self.joints = []
        self.personIdx = None
        self.jointIdx = None
        self.personColor = None

    def setClass(self, event=None):
        self.currentLabelclass = self.classcandidate.get()
        print(self.classcandidate.get())
        if self.personIdx:
            print('??')
            self.listbox.select_set(self.personIdx)
            self.listbox.event_generate("<<ListboxSelect>>")


if __name__ == '__main__':
    root = Tk()
    tool = PoseLabelTool(root)
    root.resizable(width=True, height=True)
    root.mainloop()
