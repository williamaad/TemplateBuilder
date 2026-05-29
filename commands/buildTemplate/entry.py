import traceback
import adsk.core, adsk.fusion, adsk.cam
import os
from ...lib import fusionAddInUtils as futil
from ... import config
app = adsk.core.Application.get()
ui = app.userInterface


# TODO *** Specify the command identity information. ***
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_cmdDialog'
CMD_NAME = 'Build Lichen Template'
CMD_Description = 'Builds template file for CAM setup'

# Specify that the command will be promoted to the panel.
IS_PROMOTED = True

# TODO *** Define the location where the command button will be created. ***
# This is done by specifying the workspace, the tab, and the panel, and the 
# command it will be inserted beside. Not providing the command to position it
# will insert it at the end.
WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'LichenToolsPanel'
COMMAND_BESIDE_ID = 'ScriptsManagerCommand'

# Resource location for command icons, here we assume a sub folder in this directory named "resources".
ICON_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', '')

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []
opsInputs = []
numInOpsList = 0
maxOps = 10
templates = []
buttonIds = []

# Executed when add-in is run.
def start():
    # Create a command Definition.
    cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_Description, ICON_FOLDER)

    # Define an event handler for the command created event. It will be called when the button is clicked.
    futil.add_handler(cmd_def.commandCreated, command_created)

    # ******** Add a button into the UI so the user can run the command. ********
    # Get the target workspace the button will be created in.
    workspace = ui.workspaces.itemById(WORKSPACE_ID)

    # Get the panel the button will be created in.
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    if panel == None:
        panel = workspace.toolbarPanels.add('LichenToolsPanel','Lichen Tools')#itemById(PANEL_ID)

    # Create the button command control in the UI after the specified existing command.
    control = panel.controls.addCommand(cmd_def)

    # Specify if the command is promoted to the main toolbar. 
    control.isPromoted = IS_PROMOTED


# Executed when add-in is stopped.
def stop():
    # Get the various UI elements for this command
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    command_control = panel.controls.itemById(CMD_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    # Delete the button command control
    if command_control:
        command_control.deleteMe()

    # Delete the command definition
    if command_definition:
        command_definition.deleteMe()
    for cmdId in buttonIds:
        t = ui.commandDefinitions.itemById(cmdId)
        if t:
            t.deleteMe()



# Function that is called when a user clicks the corresponding button in the UI.
# This defines the contents of the command dialog and connects to the command related events.
def command_created(args: adsk.core.CommandCreatedEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Created Event')

    # https://help.autodesk.com/view/fusion360/ENU/?contextId=CommandInputs
    inputs = args.command.commandInputs

    # TODO Define the dialog for your command by adding different inputs to the command.
    camWS = ui.workspaces.itemById('CAMEnvironment') 
    camWS.activate()
    cam: adsk.cam.CAM = app.activeDocument.products.itemByProductType('CAMProductType')
    machiningSetups = cam.setups
    library = adsk.cam.CAMManager.get().libraryManager
    machineLibrary = library.machineLibrary
    url = machineLibrary.urlByLocation(adsk.cam.LibraryLocations.CloudLibraryLocation)
    machines = machineLibrary.childMachines(url)
    designWS = ui.workspaces.itemById('FusionSolidEnvironment')
    designWS.activate()
    # Create a simple text box input.
    inputs.addTextBoxCommandInput('customer_name', 'Customer:', '', 1, False)
    inputs.addTextBoxCommandInput('po_number', 'PO Number:', '', 1, False)
    inputs.addTextBoxCommandInput('part_name', 'Part Name:', '', 1, False)
    roundStock = inputs.addBoolValueInput('round_stock',"Round Stock?",True)
    roundStock.value = True
    inputs.addValueInput('stock_diameter','Stock Diameter','in',adsk.core.ValueInput.createByString('1 in'))
    inputs.addValueInput('stock_along_jaw','Stock Along Jaw','in',adsk.core.ValueInput.createByString('1 in'))
    inputs.addValueInput('stock_perpendicular_to_jaw','Stock Perpendicular to Jaw','in',adsk.core.ValueInput.createByString('1 in'))
    inputs.addValueInput('stock_height','Stock Height','in',adsk.core.ValueInput.createByString('1 in'))
    if inputs.itemById('round_stock').value:
        inputs.itemById('stock_along_jaw').isVisible = False
        inputs.itemById('stock_perpendicular_to_jaw').isVisible = False
    else:
        inputs.itemById('stock_diameter').isVisible = False
    numOpsInput = inputs.addIntegerSliderCommandInput('num_ops','Number of Ops',1,maxOps)
    numInOpsList = numOpsInput.valueOne
    opsInputs = []
    for i in range(maxOps):
        n = str(1+i)
        txt1 = ["op_" + n + "_uses_softjaw","op_" + n + "_softjaw_spacing","op_" + n + "_softjaw_pocket_depth","op_"+n+"machine"]
        txt2 = ["Op " + n + " uses softjaw?","Op " + n + " Softjaw Spacing:","Op " + n + " Softjaw Pocket Depth:","Op " + n + " Machine: "] 
        opsInputs.append([inputs.addBoolValueInput(txt1[0],txt2[0],True),
                            inputs.addValueInput(txt1[1],txt2[1],"in",adsk.core.ValueInput.createByString('0.125 in')),
                            inputs.addValueInput(txt1[2],txt2[2],"in",adsk.core.ValueInput.createByString('0.35 in')),
                            inputs.addDropDownCommandInput(txt1[3],txt2[3],adsk.core.DropDownStyles.TextListDropDownStyle)])
        dropDownItems = opsInputs[i][3].listItems
        for m in machines:
            dropDownItems.add(m.model,False)
        for j in range(1,3):
            opsInputs[i][j].isVisible = False
        if i >= numInOpsList:
            for j in range(4):
                opsInputs[i][j].isVisible = False
            
    
    
    


    # TODO Connect to the events that are needed by this command.
    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(args.command.executePreview, command_preview, local_handlers=local_handlers)
    futil.add_handler(args.command.validateInputs, command_validate_input, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)


# This event handler is called when the user clicks the OK button in the command dialog or 
# is immediately called after the created event not command inputs were created for the dialog.
def command_execute(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Execute Event')



    # Get a reference to your command's inputs.
    inputs = args.command.commandInputs
    template = LichenTemplate(inputs)
    templates.append(template)
    bodySelectionCount = len(template.bodySelections)
    if(bodySelectionCount>0):
        cmdDef = template.bodySelections[bodySelectionCount-1]
        tempId = "template"+str(template.number)+"bodySelection" + str(cmdDef.index)
        tempName = "Body Selection " + str(cmdDef.index)
        button = ui.commandDefinitions.addButtonDefinition(tempId,tempName,"")
        buttonIds.append(tempId)
        button.commandCreated.add(cmdDef)
        button.execute()
    else:
        template.nextStep()

    # Do something interesting


# This event handler is called when the command needs to compute a new preview in the graphics window.
def command_preview(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Preview Event')
    inputs = args.command.commandInputs


# This event handler is called when the user changes anything in the command dialog
# allowing you to modify values of other inputs based on that change.
def command_input_changed(args: adsk.core.InputChangedEventArgs):
    changed_input = args.input
    inputs = args.inputs
    if changed_input.id=='round_stock':
        if changed_input.value:
            inputs.itemById('stock_along_jaw').isVisible = False
            inputs.itemById('stock_perpendicular_to_jaw').isVisible = False
            inputs.itemById('stock_diameter').isVisible = True
        else:
            inputs.itemById('stock_diameter').isVisible = False
            inputs.itemById('stock_along_jaw').isVisible = True
            inputs.itemById('stock_perpendicular_to_jaw').isVisible = True
    if changed_input.id=='num_ops':
        newCount = changed_input.valueOne
        for i in range(maxOps):
            n = str(1+i)
            txt = ["op_" + n + "_uses_softjaw","op_" + n + "_softjaw_spacing","op_" + n + "_softjaw_pocket_depth","op_"+n+"machine"]
            if i < newCount:
                inputs.itemById(txt[0]).isVisible = True
                inputs.itemById(txt[3]).isVisible = True
                
            else:
                inputs.itemById(txt[0]).isVisible = False
                inputs.itemById(txt[3]).isVisible = False
                
    for i in range(maxOps):
        n = str(1+i)
        txt = ["op_" + n + "_uses_softjaw","op_" + n + "_softjaw_spacing","op_" + n + "_softjaw_pocket_depth","op_"+n+"machine"]
        count = inputs.itemById('num_ops').valueOne
        if inputs.itemById(txt[0]).value:
            if i <count:
                inputs.itemById(txt[1]).isVisible = True
                inputs.itemById(txt[2]).isVisible = True
            else:
                inputs.itemById(txt[1]).isVisible = False
                inputs.itemById(txt[2]).isVisible = False
        else:
            inputs.itemById(txt[1]).isVisible = False
            inputs.itemById(txt[2]).isVisible = False
    # General logging for debug.
    futil.log(f'{CMD_NAME} Input Changed Event fired from a change to {changed_input.id}')


# This event handler is called when the user interacts with any of the inputs in the dialog
# which allows you to verify that all of the inputs are valid and enables the OK button.
def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Validate Input Event')

    inputs = args.inputs
    args.areInputsValid = True
        

# This event handler is called when the command terminates.
def command_destroy(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Destroy Event')

    global local_handlers
    #local_handlers = []


class LichenTemplate:
    def addParameter(self,param,useDefaults):
            valueEntered = None
            if useDefaults:
                valueEntered = param[2]
            else:
                msg = "Please enter " + str(param[0]) + ": "
                (valueEntered, isCancelled) = ui.inputBox(msg, str(param[0]), str(param[2]))
                if isCancelled:
                    valueEntered = param[2]
            if param[1] == "text":
                valueEntered = str("\'" + valueEntered + "\'")
            val = adsk.core.ValueInput.createByString(valueEntered)
            self.params.add(param[0],val,param[1],"") 

    def createJointComponent(self,parent: adsk.fusion.component,name: str):
        comp = parent.component.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        comp.component.name = name
        jointOrigins = comp.component.jointOrigins
        jointInput = jointOrigins.createInput(adsk.fusion.JointGeometry.createByPoint(comp.component.originConstructionPoint))
        jointOrigin = jointOrigins.add(jointInput)
        jointOrigin.name = name
        return comp
    
    def circleSketch(self,stockSketch):
        circle = stockSketch.sketchCurves.sketchCircles.addByCenterRadius(stockSketch.sketchPoints.item(0),1.0)
        diameterDimension = stockSketch.sketchDimensions.addDiameterDimension(circle,adsk.core.Point3D.create(0,1,0))
        diameterDimension.parameter.expression = "stockDiameter"

    def rectSketch(self,stockSketch):
        l = self.params.itemByName("stockAlongJaw").value
        w = self.params.itemByName("stockPerpendicularToJaw").value
        points = stockSketch.sketchPoints
        points.add(adsk.core.Point3D.create(l/2,-w/2,0))
        points.add(adsk.core.Point3D.create(l/2,w/2,0))
        points.add(adsk.core.Point3D.create(-l/2,w/2,0))
        points.add(adsk.core.Point3D.create(-l/2,-w/2,0))
        dimensions = stockSketch.sketchDimensions
        orientation = adsk.fusion.DimensionOrientations.AlignedDimensionOrientation
        lines = stockSketch.sketchCurves.sketchLines
        lines.addByTwoPoints(points.item(1),points.item(3))
        lines.item(0).isConstruction = True
        constraints = stockSketch.geometricConstraints
        constraints.addMidPoint(points.item(0),lines.item(0))
        lines.addByTwoPoints(points.item(2),points.item(4))
        lines.item(1).isConstruction = True
        constraints.addMidPoint(points.item(0),lines.item(1))
        for j in range(4):
            lines.addByTwoPoints(points.item(j+1),points.item((j+1)%4+1))
        constraints.addVertical(lines.item(2))
        constraints.addHorizontal(lines.item(3))
        alongJaw = dimensions.addDistanceDimension(points.item(1),points.item(2),orientation,adsk.core.Point3D.create(0,0,0))
        perpToJaw = dimensions.addDistanceDimension(points.item(2),points.item(3),orientation,adsk.core.Point3D.create(0,0,0))
        alongJaw.parameter.expression = "stockAlongJaw"
        perpToJaw.parameter.expression = "stockPerpendicularToJaw"

    def selectCloudComponent(self,txt: str):
        fileDlg = ui.createCloudFileDialog()
        fileDlg.isMultiSelectEnabled = False
        fileDlg.title = txt
        initialFolder = None
        try:
            initialFolder = self.data.activeProject.rootFolder.dataFolders.itemByName("CAM Templates").dataFolders.itemByName("FixtureAssemblies")
        except:
            initialFolder = self.data.activeProject.rootFolder
        fileDlg.dataFolder = initialFolder
        dlgResult = fileDlg.showOpen()
        if dlgResult == adsk.core.DialogResults.DialogOK:
            
            return fileDlg.dataFile
        return ""
    def selectCloudCustomerComponent(self,txt: str):
        fileDlg = ui.createCloudFileDialog()
        fileDlg.isMultiSelectEnabled = False
        fileDlg.title = txt
        initialFolder = None
        try:
            initialFolder = self.data.activeProject.rootFolder.dataFolders.itemByName("Customer Projects")
            maybeCustomer = None
            maybePo = None
            maybePart = None
            try:
                maybeCustomer = initialFolder.dataFolders.itemByName(self.params.itemByName("customer").textValue)
            except:
                maybeCustomer = None

            if maybeCustomer:
                initialFolder = maybeCustomer
                try:
                    maybePo = initialFolder.dataFolder.itemByName(self.params.itemByName("poNumber").textValue)
                except:
                    maybePo = None
            if maybePo:
                initialFolder = maybePo
                try:
                    maybePart = initialFolder.dataFolder.itemByName(self.params.itemByName("partName").textValue)
                except:
                    maybePart = None
            if maybePart:
                initialFolder = maybePart
        except:
            initialFolder = self.data.activeProject.rootFolder
        fileDlg.dataFolder = initialFolder
        dlgResult = fileDlg.showOpen()
        if dlgResult == adsk.core.DialogResults.DialogOK:
            
            return fileDlg.dataFile
        return None
    def searchForOccurrence(self,occ: Occurrence,targ: str):
        occurrences = occ.childOccurrences
        for i in range(occurrences.count):
            o = occurrences.item(i)
            #ui.messageBox(str(o.component.name))
            if o.component.name == targ:
                return o#.createForAssemblyContext(occ)
        return None
    def recursiveName(self,occurrence):
        parent = None
        if occurrence == None:
            return "?"
        if occurrence.classType() == adsk.fusion.JointGeometry.classType():
            if occurrence.entityOne.classType() == adsk.fusion.BRepFace.classType():
                occurrence = occurrence.entityOne.body
            else:
                return str(occurrence.entityOne.classType())
        parent = occurrence.assemblyContext
        if parent == None:
            return occurrence.name
        return self.recursiveName(parent) + " > " + occurrence.name
    def createPlanarJointInput(self,joints,j1,j2,flipped):
        jointInput = joints.createInput(j1,j2)
        jointInput.setAsPlanarJointMotion(adsk.fusion.JointDirections.ZAxisJointDirection)
        jointInput.angle = adsk.core.ValueInput.createByString("0")
        jointInput.offset = adsk.core.ValueInput.createByString("0")
        jointInput.isFlipped = flipped
        return jointInput
    def createRigidJointInput(self,joints,j1,j2,flipped):
        jointInput = joints.createInput(j1,j2)
        jointInput.setAsRigidJointMotion()
        jointInput.isFlipped = flipped
        return jointInput
    def createRevoluteJointInput(self,joints,j1,j2,flipped):
        jointInput = joints.createInput(j1,j2)
        jointInput.setAsRevoluteJointMotion(adsk.fusion.JointDirections.ZAxisJointDirection)
        jointInput.angle = adsk.core.ValueInput.createByString("0")
        jointInput.offset = adsk.core.ValueInput.createByString("0")
        jointInput.isFlipped = flipped
        return jointInput
    def createJoint(self,joints,jointInput):
        entity1 = jointInput.geometryOrOriginOne
        entity2 = jointInput.geometryOrOriginTwo
        name1 = self.recursiveName(jointInput.geometryOrOriginOne)
        name2 = self.recursiveName(jointInput.geometryOrOriginTwo)
        name = str(name1) + " to " + str(name2)
        joint = None
        try:
            joint = joints.add(jointInput)
            joint.name = name
            return joint
        except Exception as e:
            ui.messageBox(traceback.format_exc())
            return None
    def __init__(self,inputs):
        self.number = len(templates)-1
        self.inputs = inputs
        self.doc = app.activeDocument
        self.products = self.doc.products
        self.data = app.data
        self.design = adsk.fusion.Design.cast(app.activeProduct)
        self.root = self.design.rootComponent
        self.params = self.design.userParameters
        self.design.designIntent = adsk.fusion.DesignIntentTypes.HybridDesignIntentType
        self.templateParameters = [["customer","text",self.inputs.itemById("customer_name").text],
                                   ["poNumber","text",self.inputs.itemById("po_number").text],
                                   ["partName","text",self.inputs.itemById("part_name").text]]
        #Ask for input about stock Shape
        self.roundStock = self.inputs.itemById('round_stock').value
        self.softjawComponents=[]
        #CAM init
        camWS = ui.workspaces.itemById('CAMEnvironment') 
        camWS.activate()
        self.cam: adsk.cam.CAM = self.products.itemByProductType('CAMProductType')
        self.machiningSetups = self.cam.setups
        self.library = adsk.cam.CAMManager.get().libraryManager
        self.machineLibrary = self.library.machineLibrary
        url = self.machineLibrary.urlByLocation(adsk.cam.LibraryLocations.CloudLibraryLocation)
        self.machines = self.machineLibrary.childMachines(url)
        designWS = ui.workspaces.itemById('FusionSolidEnvironment')
        designWS.activate()

        joints = self.root.joints
        if self.roundStock:
            self.templateParameters.append(["stockDiameter","in",self.inputs.itemById("stock_diameter").expression])
        else:
            self.templateParameters.append(["stockAlongJaw","in",self.inputs.itemById("stock_along_jaw").expression])
            self.templateParameters.append(["stockPerpendicularToJaw","in",self.inputs.itemById("stock_perpendicular_to_jaw").expression])
        self.templateParameters.append(["stockHeight","in",self.inputs.itemById("stock_height").expression])
        numOps = self.inputs.itemById('num_ops').valueOne
        self.ops = []
        for i in range(numOps):
            n = str(i+1)
            txt1 = ["op_" + n + "_uses_softjaw","op_" + n + "_softjaw_spacing","op_" + n + "_softjaw_pocket_depth",]
            txt2 = ["op" + n,"op" + n + "SoftjawSpacing","op" + n + "SoftjawPocketDepth"]
            usesSoftjaws = self.inputs.itemById(txt1[0]).value
            machineSelection = None
            machineInputItem = self.inputs.itemById("op_"+n+"machine").selectedItem
            if machineInputItem:
                machineSelection = machineInputItem.name
            if usesSoftjaws:
                self.ops.append([txt2[0],True,machineSelection])
                self.templateParameters.append([txt2[1],"in",self.inputs.itemById(txt1[1]).expression])
                self.templateParameters.append([txt2[2],"in",self.inputs.itemById(txt1[2]).expression])
            else:
                self.ops.append([txt2[0],False,machineSelection])

        #Set userParameters 
        for p in self.templateParameters:
            self.addParameter(p,True)
        
        #add(name, value, units, comment)


        
        #Create Stock Component
        self.stock = self.root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        self.stock.component.name = "Stock"
        
        stockViseAttachment = self.createJointComponent(self.stock,"stockViseAttachment")
        stockPartAttachment = self.createJointComponent(self.stock,"stockPartAttachment")
        stockViseAttachment.isGroundToParent = False

        stockJawAttachment = None
        if not(self.roundStock):
            stockJawAttachment = self.createJointComponent(self.stock,"stockJawAttachment")
        stockSketch = self.stock.component.sketches.add(self.stock.component.xYConstructionPlane)
        if self.roundStock:
            stockSketch.name = "Round Stock Sketch"
            self.circleSketch(stockSketch)
        else:
            stockSketch.name = "Rectangle Stock Sketch"
            self.rectSketch(stockSketch)
        prof = stockSketch.profiles.item(0)
        extrudes = self.stock.component.features.extrudeFeatures
        extrudeDistance = adsk.core.ValueInput.createByString("stockHeight")
        extrude1 = extrudes.addSimple(prof,extrudeDistance,adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        body1 = extrude1.bodies.item(0)
        body1.name = "stockBody"
        body1.opacity = .5
        startFace = extrude1.startFaces.item(0)
        endFace = extrude1.endFaces.item(0)#stock.component.joints
        bottom = adsk.fusion.JointGeometry.createByPlanarFace(startFace,None,adsk.fusion.JointKeyPointTypes.CenterKeyPoint)
        top = adsk.fusion.JointGeometry.createByPlanarFace(endFace,None,adsk.fusion.JointKeyPointTypes.CenterKeyPoint)
        bottomJointInput = joints.createInput(stockViseAttachment.component.jointOrigins.item(0),bottom)
        topJointInput = joints.createInput(stockPartAttachment.component.jointOrigins.item(0),top)
        bottomJointInput.setAsRigidJointMotion()
        topJointInput.setAsRigidJointMotion()
        bottomJoint = self.createJoint(joints,bottomJointInput)#stockJoints.add(bottomJointInput)
        topJoint = self.createJoint(joints,topJointInput)#stockJoints.add(topJointInput)
        self.params.add("stockOffset",adsk.core.ValueInput.createByString("-.02"),"in","")
        topJoint.offset.expression="stockOffset"
        sideJoint = None
        if not(self.roundStock):
            side = adsk.fusion.JointGeometry.createByPlanarFace(body1.faces.item(2),None,adsk.fusion.JointKeyPointTypes.CenterKeyPoint)
            sideJointInput = joints.createInput(stockJawAttachment.component.jointOrigins.item(0),side)
            sideJointInput.setAsRigidJointMotion()
            sideJoint = self.createJoint(joints,sideJointInput)#stockJoints.add(sideJointInput)
        
        self.setups = []
        opCount = 0
        self.fas = []
        #create setups
        for op in self.ops:
            occurrence = self.root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            occurrence.component.name = str(op[0] + " Setup")
            fixture = None
            softJawPart = None
            softJawStock = None
            if op[1] : #if softjaw
                softJawPart = occurrence.component.occurrences.addNewComponent(adsk.core.Matrix3D.create())
                softJawPart.component.name = str(op[0] + " Soft Jaw Part")
                softJawStock = occurrence.component.occurrences.addNewComponent(adsk.core.Matrix3D.create())
                softJawStock.component.name = str(op[0] + " Soft Jaw Stock")
                self.softjawComponents.append([softJawPart,softJawStock])
            else:
                self.softjawComponents.append([None,None])
            fixture = occurrence.component.occurrences.addNewComponent(adsk.core.Matrix3D.create()).createForAssemblyContext(occurrence)
            fixture.component.name = str(op[0] + " Fixture Assembly")
            filePath = self.selectCloudComponent(str("Please select a fixture assembly for " + op[0]))
            #dummy = createJointComponent(fixture,"dummy")
            fa = fixture.component.occurrences.addByInsert(filePath,adsk.core.Matrix3D.create(),True).createForAssemblyContext(fixture)
            fa.isGroundToParent = False
            self.fas.append(fa)
            adsk.doEvents()
            #dummy.deleteMe()
            if op[1]: #if softjaw
                #join jaw 1 to jaw 2
                vise = None
                j1 = None
                j2 = None
                for i in range(fa.component.occurrences.count):
                    vise = fa.childOccurrences.item(i)#.createForAssemblyContext(fa)
                    j1 = self.searchForOccurrence(vise,"Jaw Position 1")
                    j2 = self.searchForOccurrence(vise,"Jaw Position 2")
                    if j1 and j2:
                        j1Origin = j1.component.jointOrigins.item(0).createForAssemblyContext(j1)#adsk.fusion.JointGeometry.createByPoint(j1.component.originConstructionPoint)
                        j2Origin = j2.component.jointOrigins.item(0).createForAssemblyContext(j2)#adsk.fusion.JointGeometry.createByPoint(j2.component.originConstructionPoint)
                        tempJointInput = self.createPlanarJointInput(joints,j1Origin,j2Origin,True)
                        joint = self.createJoint(joints,tempJointInput)
                        joint.offset.expression = str("-" + op[0] + "SoftjawSpacing")
                        j1 = None
                        j2 = None
            if opCount == 0:#join stock to Op 1 vise
                txt = str(op[0])+"StockOffsetAlongJaw"
                self.params.add(txt,adsk.core.ValueInput.createByString("0"),"in","")
                if op[1]:
                    txt = str(op[0])+"StockOffsetPerpendicularToJaw"
                    self.params.add(txt,adsk.core.ValueInput.createByString("0"),"in","")
                stockAttachment = self.searchForOccurrence(fa,"StockAttachment")
                geo1 = stockAttachment.component.jointOrigins.item(0).createForAssemblyContext(stockAttachment)
                geo2 = stockViseAttachment.component.jointOrigins.item(0).createForAssemblyContext(stockViseAttachment)
                tempJointInput = None
                joint = None
                if self.roundStock:
                    tempJointInput = self.createRigidJointInput(joints,geo1,geo2,True)
                    joint = self.createJoint(joints,tempJointInput)
                else:
                    tempJointInput = self.createRevoluteJointInput(joints,geo1,geo2,True)
                    joint = self.createJoint(joints,tempJointInput)
                    geo1 = None
                    for i in range(fa.childOccurrences.count): #join jaw position 1 of any vise in fixture assembly to stock side attachment.
                        vise = fa.childOccurrences.item(i)
                        j1 = self.searchForOccurrence(vise,"Jaw Position 1")
                        if j1:
                            geo1 = j1.component.jointOrigins.item(0).createForAssemblyContext(j1)
                            geo2 = stockJawAttachment.component.jointOrigins.item(0).createForAssemblyContext(stockJawAttachment)
                            tempJointInput = self.createPlanarJointInput(joints,geo1,geo2,False)
                            tjoint = self.createJoint(joints,tempJointInput)
                
                joint.offsetX.expression = str(op[0])+"StockOffsetAlongJaw"
                if op[1]:
                    joint.offsetY.expression = str(op[0])+"StockOffsetPerpendicularToJaw"
                    joint.offset.expression = str("-" + op[0] + "SoftjawPocketDepth")
            self.setups.append(occurrence)
            opCount+=1
                

        #Create Part
        self.partHolder = self.root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        self.partHolder.component.name = "Part"
        opAttachments = []
        self.bodySelections = []
        lastTrigger = None
        for i in range(len(self.ops)):
            opAttachments.append(self.createJointComponent(self.partHolder,self.ops[i][0] + " Attachment"))

            if self.ops[i][1]:
                selectBodies = multiSelectCreatedEventHandler(self,self.setups,self.ops,i,lastTrigger)
                self.bodySelections.append(selectBodies)
                lastTrigger = selectBodies
            if i == 0: #Join Op 1 to stock
                geo1 = opAttachments[i].component.jointOrigins.item(0).createForAssemblyContext(opAttachments[i])
                geo2 = stockPartAttachment.component.jointOrigins.item(0).createForAssemblyContext(stockPartAttachment)
                tempJointInput = self.createRigidJointInput(joints,geo1,geo2,False)
                self.createJoint(joints,tempJointInput)
            if i == 1: #Join Op 2 to Op 1
                geo1 = opAttachments[0].component.jointOrigins.item(0).createForAssemblyContext(opAttachments[0])
                geo2 = opAttachments[1].component.jointOrigins.item(0).createForAssemblyContext(opAttachments[1])
                tempJointInput = self.createRigidJointInput(joints,geo1,geo2,True)
                joint = self.createJoint(joints,tempJointInput)

            #join ops to fixtures
            if i>0: 
                txt = [str(self.ops[i][0]) + "OffsetAlongJaw",str(self.ops[i][0]) + "OffsetPerpendicularToJaw",str(self.ops[i][0]) + "AttachmentAngle"]
                self.params.add(txt[0],adsk.core.ValueInput.createByString("0"),"in","")
                self.params.add(txt[1],adsk.core.ValueInput.createByString("0"),"in","")
                self.params.add(txt[2],adsk.core.ValueInput.createByString("0"),"deg","")
                geo1 = opAttachments[i].component.jointOrigins.item(0).createForAssemblyContext(opAttachments[i])
                j2 = self.searchForOccurrence(self.fas[i],"StockAttachment")
                geo2 = j2.component.jointOrigins.item((0)).createForAssemblyContext(j2)
                if geo1 and geo2:
                    tempJointInput = self.createRigidJointInput(joints,geo1,geo2,False)
                    joint = self.createJoint(joints,tempJointInput)
                    joint.offsetY.expression = txt[0]
                    joint.offsetX.expression = txt[1]
                    joint.angle.expression = txt[2]
                    if self.ops[i][1]:
                        joint.offset.expression = "-" + str(self.ops[i][0]) + "SoftjawPocketDepth"
        partData = self.selectCloudCustomerComponent("Please Select a Part")
        self.partComponent = None
        if partData:
            self.partComponent = self.partHolder.component.occurrences.addByInsert(partData,adsk.core.Matrix3D.create(),True)
    def nextStep(self):
        #Bring in WCS Components
        try:
            wcsFolder = self.data.activeProject.rootFolder.dataFolders.itemByName("CAM Templates").dataFolders.itemByName("FixtureAssemblies").dataFolders.itemByName("WCS")
            wcsFile = wcsFolder.dataFiles.item(0)
            joints = self.root.joints
            wcs = []
            for i in range(len(self.setups)):
                wcs.append(self.setups[i].component.occurrences.addByInsert(wcsFile,adsk.core.Matrix3D.create(),True).createForAssemblyContext(self.setups[i]))
                fixtureWcs = self.searchForOccurrence(self.fas[i],"WCSAttachment")
                j1 = wcs[i].component.jointOrigins.item(0).createForAssemblyContext(wcs[i])
                j2 = fixtureWcs.component.jointOrigins.item(0).createForAssemblyContext(fixtureWcs)
                jointInput = self.createRigidJointInput(joints,j1,j2,False)
                joint = self.createJoint(joints,jointInput)
                txt = "op" + str(i+1) + "OriginZHeight"
                self.params.add(txt,adsk.core.ValueInput.createByString("2.895 in"),"in","")
                joint.offset.expression = txt
                joint.angle.expression = "-90 deg"
                joint.name = "*edit*" + joint.name
                #wcs[i].isLightBulbOn = False
            camWS = ui.workspaces.itemById('CAMEnvironment') 
            camWS.activate()
            for i in range(len(self.ops)):#create Ops
                setupInput = None#self.machiningSetups.createInput(adsk.cam.OperationTypes.MillingOperation)
                machine = None
                for m in self.machines:
                    if m.model == self.ops[i][2]:
                        machine= m
                if machine:
                    setupInput = self.machiningSetups.createInput(adsk.cam.OperationTypes.MillingOperation)
                    setupInput.machine = machine
                    setupInput.models = [self.partHolder]
                    setupInput.name = str(machine.model + " " + self.ops[i][0])
                    if i == 0:
                        setupInput.stockMode = adsk.cam.SetupStockModes.SolidStock
                        setupInput.stockSolids = [self.stock]
                    else:
                        setupInput.stockMode = adsk.cam.SetupStockModes.PreviousSetupStock
                    if self.ops[i][1]:
                        setupInput.fixtures = [self.softjawComponents[i][0]]
                    else:
                        setupInput.fixtures = [self.fas[i]]
                    
                    setup = self.machiningSetups.add(setupInput)
                    camParameters = setup.parameters
                    camParameters.itemByName("job_programName").expression = "\'O" + str(2001 + i) + "\'"
                    camParameters.itemByName("job_programComment").expression = "\'" + self.params.itemByName("partName").textValue + " " + self.ops[i][0] + "\'"
                    camParameters.itemByName("job_workOffset").expression = str(i+1)
                    camParameters.itemByName("wcs_orientation_mode").expression = "\'axesZX\'"
                    camParameters.itemByName("wcs_origin_mode").expression = "\'point\'"
            for i in range(len(self.ops)):#create Softjaw Ops
                if self.ops[i][1]:
                    setupInput = None#self.machiningSetups.createInput(adsk.cam.OperationTypes.MillingOperation)
                    machine = None
                    for m in self.machines:
                        if m.model == self.ops[i][2]:
                            machine= m
                    if machine:
                        setupInput = self.machiningSetups.createInput(adsk.cam.OperationTypes.MillingOperation)
                        setupInput.machine = machine
                        setupInput.models = [self.softjawComponents[i][0]]
                        setupInput.name = str(machine.model +" " + self.ops[i][0] + " softjaw")
                        if i == 0:
                            setupInput.stockMode = adsk.cam.SetupStockModes.SolidStock
                            setupInput.stockSolids = [self.softjawComponents[i][1]]
                        else:
                            setupInput.stockMode = adsk.cam.SetupStockModes.PreviousSetupStock
                        
                        
                        setup = self.machiningSetups.add(setupInput)
                        camParameters = setup.parameters
                        camParameters.itemByName("job_programName").expression = "\'O" + str(2001 + i) + "\'"
                        camParameters.itemByName("job_programComment").expression = "\'" + self.params.itemByName("partName").textValue + " " + self.ops[i][0] + " Softjaw\'"
                        camParameters.itemByName("job_workOffset").expression = str(i+1)
                        camParameters.itemByName("wcs_orientation_mode").expression = "\'axesZX\'"
                        camParameters.itemByName("wcs_origin_mode").expression = "\'point\'"
                    
                    

        except Exception as e:
            ui.messageBox(traceback.format_exc())
            return None
class multiSelectCreatedEventHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self,template,setups,ops,index,lastTrigger):

        super().__init__()
        self.template = template
        self.setups = setups
        self.ops = ops
        self.index = index
        self.lastTrigger = lastTrigger
    def notify(self,args):
        eventArgs = adsk.core.CommandCreatedEventArgs.cast(args)

        cmd = eventArgs.command
        inputs = cmd.commandInputs
        for child in self.template.root.occurrences:
            child.isLightBulbOn = False
        self.setups[self.index].isLightBulbOn = True
        msg = "Please select body or bodies for " + self.ops[self.index][0] + " softjaw"
        shrtmsg = "" + self.ops[self.index][0] + " Softjaw Bodies: "
        selectionInput = inputs.addSelectionInput('bodySelection', shrtmsg , msg)
        selectionInput.addSelectionFilter('SolidBodies')
        selectionInput.setSelectionLimits(1, 0)

        # Connect to the execute event.
        onExecute = MultiSelectExecuteHandler(self.template,self.setups,self.index,self.lastTrigger)
        cmd.execute.add(onExecute)
        local_handlers.append(onExecute)
class MultiSelectExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self,template,setups,index,lastTrigger):
        super().__init__()
        self.template = template
        self.setups = setups
        self.index = index
        self.lastTrigger = lastTrigger
    def notify(self, args):
        try:
            eventArgs = adsk.core.CommandEventArgs.cast(args)

            # Get the values from the command inputs.
            inputs = eventArgs.command.commandInputs

            selections = inputs.itemById('bodySelection')
            count = selections.selectionCount
            bodies = adsk.core.ObjectCollection.create()
            for i in range(count):
                bodies.add(selections.selection(i).entity)
            bounds = self.template.root.boundingBox2(0)
            p1 = [bounds.minPoint.x,bounds.minPoint.y,bounds.minPoint.z]
            p2 = [bounds.maxPoint.x,bounds.maxPoint.y,bounds.maxPoint.z]
            for i in range(len(p1)):
                p1[i] = abs(p1[i])
                p2[i] = abs(p2[1])
            x = p1[0]+p2[0]+1
            y = p2[1]+p2[1]+1
            z = p1[2]+p2[2]+1
            partOccurrence = self.template.softjawComponents[self.index][0]
            stockOccurrence = self.template.softjawComponents[self.index][1]
            self.makeSoftjaw(partOccurrence,x,y,z,bodies)
            self.makeSoftjaw(stockOccurrence,x,y,z,bodies)
            stockOccurrence.isLightBulbOn = False

            bodiesArray = bodies.asArray()
            for b in bodiesArray:
                b.isLightBulbOn = False
            if self.lastTrigger == None:
                for child in self.template.root.occurrences:
                    child.isLightBulbOn = True
                self.template.nextStep()
            else: 
                tempId = "template"+str(self.template.number)+"bodySelection" + str(self.lastTrigger.index)
                tempName = "Body Selection " + str(self.lastTrigger.index)
                button = ui.commandDefinitions.addButtonDefinition(tempId,tempName,"")
                buttonIds.append(tempId)
                button.commandCreated.add(self.lastTrigger)
                button.execute()
            
        except Exception as e:
            ui.messageBox(traceback.format_exc())
            return None
    def createBody(self,targ,x,y,z):
        point = adsk.core.Point3D.create(x,y,z)
        tsketch = targ.sketches.add(self.template.root.xYConstructionPlane)
        circles = tsketch.sketchCurves.sketchCircles
        circle1 = circles.addByCenterRadius(point, 0.5)
        prof = tsketch.profiles.item(0)
        distance = adsk.core.ValueInput.createByString("0.5 in")
        extrudes = targ.features.extrudeFeatures
        extrusion = extrudes.addSimple(prof, distance, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        tempBody = extrusion.bodies.item(0)
        #tsketch.deleteMe()
        return tempBody
    def makeSoftjaw(self,occ,x,y,z,bodies):
        tempBody = self.createBody(occ.component,x,y,z)
        featInput = self.template.root.features.combineFeatures.createInput(tempBody,bodies)
        featInput.isKeepToolBodies = True
        occ.component.features.combineFeatures.add(featInput)
        occ.component.features.removeFeatures.add(tempBody)
