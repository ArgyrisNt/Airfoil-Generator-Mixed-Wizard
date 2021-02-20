# Python Script, API Version = V18.

# Issues to consider:
# 1) If user has selected to create an airfoil without cutting the edge (CutTE = No), then the creation of a valid 
#    rectangle domain(or enclosure) is not possible. As a result, the creation of a mesh will be problematic.
# 2) On last step, Mechanical will be launching in order to generate a mesh. After the generation, the software will close 
#    automatically. There might be the option to generate a mesh, without launching Mechanical.
# 3) If user adds a new step, then an <onreset> function(is called when back button is pressed) for step "Mesh" should 
#    be defined. This function will delete old mesh controls.
# 4) In the function named CreateMesh, there are some commands as comments. With these commands, a sizing children of mesh
#    object is created and the input values are defined to this children. Although, there is not possible to activate
#    CaptureCurvature and CaptureProximity in this way. 

import units
import math
import System
import sys
import clr
import os
clr.AddReference("Ans.Utilities")
from Ansys.Utilities import ApplicationConfiguration

ansysDir = ApplicationConfiguration.DefaultConfiguration.AwpRootEnvironmentVariableValue
scdmlib = os.path.join(ansysDir,"scdm","Scripting")

execfile(os.path.join(scdmlib, "LoadSCDMAPIModuleV18.py"))
execfile(os.path.join(scdmlib, "LoadSCDMAPITypesV18.py"))
execfile(os.path.join(scdmlib, "LoadSCDMAPIUtilitiesV18.py"))
execfile(os.path.join(scdmlib, "UtilitiesOnLoadV18.py"))

geoSystem = None

# Drop down menu to define cut trailing value.(If cut trailing is selected)
def ShowCutValue(step,property):
    selection = step.Properties["Cut Trailing/CutTE"].ValueString
    if selection == "Yes":
	    return True
    else:
	    return False

# Drop down menu to define WingSpan value.(If 3D mode is selected)
def ShowWingSpanValue(step,property):
    selection = step.PreviousStep.PreviousStep.Properties["2Dor3D"].ValueString
    if selection != "2D":
	    return True
    else:
	    return False

# Drop down menu to define 2D domain.(If 2D mode is selected)
def Show2dDomainValues(step,property):
    selection = step.PreviousStep.PreviousStep.PreviousStep.Properties["2Dor3D"].ValueString
    if selection == "2D":
	    return True
    else:
	    return False

# Drop down menu to define 3D Enclosure.(If 3D mode is selected)
def Show3dEnclosureValues(step,property):
    selection = step.PreviousStep.PreviousStep.PreviousStep.Properties["2Dor3D"].ValueString
    if selection != "2D":
	    return True
    else:
	    return False
		
# Check if Naca code is valid.
def NacaValidation(step,property):
    Naca = step.Properties["Naca"].ValueString
    j = 0
    for i in Naca:
	    j += 1
    if j!= 4:
        MessageBox.Show(" Invalid Naca code! Naca code must be 4 digits long, not " +j.ToString()+". ")
    else:
        if float(Naca[2]) == 0 and float(Naca[3]) == 0:
	        MessageBox.Show(" Thickness is too small (minimum is 01)")
        if float(Naca[2]) == 3 and float(Naca[3]) != 0:
	        MessageBox.Show(" Thickness is too big (maximum is 30)")
        if float(Naca[2]) > 3:
            MessageBox.Show(" Thickness is too big (maximum is 30)")

# Check if Angle of Attack is valid.
def AngleOfAttackValidation(step,property):
    Angle = step.Properties["Angle"].Value
    if Angle < 0.0 or Angle > 180.0:
        MessageBox.Show(" Invalid Angle!")

# Select and delete everything.
def DeleteAllVisible():
    selection = Selection.SelectAll()
    if selection.Items.Count > 0:
        result = Delete.Execute(selection)
    return

# Calculate airfoil thickness for NACA 4-digit series and returns x,y coords. 
def CreateAirfoil(m,p,t,x):
    y_upper = range(0,len(x),1) 
    y_lower = range(0,len(x),1)
    thickness  = range(0,len(x),1)
    print("stage 1")
    for i in range(0,len(x),1):
        thickness[i] = t / 0.20 * (0.29690 * math.sqrt(x[i]) - 0.12600 * x[i] - 0.35160 *
        math.pow(x[i], 2) + 0.28430 * math.pow(x[i], 3) - 0.10360 *
        math.pow(x[i], 4))
        
    fwd_x = [i for i in x if i<p]
    aft_x =[i for i in x if i>=p]
    
    if 0<p<1 and 0<m<1:
        fwd_camber =  [0 for i in range(0,len(fwd_x),1)]
        aft_camber =  [0 for i in range(0,len(aft_x),1)]
        for i in range(0,len(fwd_x),1):
            fwd_camber[i] = m / p**2 * (2 * p * fwd_x[i] - math.pow(fwd_x[i], 2))
        for i in range(0,len(aft_x),1):
            aft_camber[i] = m / (1 - p)**2 * ((1 - 2 * p) + 2 * p * aft_x[i] -math.pow(aft_x[i], 2))
        
        camber = fwd_camber + aft_camber
    else:
        camber = [0 for i in range(0,len(x),1)]
     
    y_upper = [camber[i]+thickness[i] for i in range(len(thickness))]
    y_lower = [camber[i]-thickness[i] for i in range(len(thickness))]
     
    x_upper = x[::-1]
    x_lower = x[0:]

    y_upper = y_upper[::-1]
    y_lower = y_lower[0:]

    x = x_upper + x_lower
    y = y_upper + y_lower

    y [0] = 0.0
    y[-1] = 0.0
    return (x, y)

# Create list of 2D Points with given x,y coords. 
def Point2DList(x,y, draw):
    points = List[Point2D]()
    
    if draw:
        for i in range(0,len(x),1):
            point = Point2D.Create(x[i], y[i])
            points.Add(point)
            SketchPoint.Create(point)
    else:
        for i in range(0,len(x),1):
            point = Point2D.Create(x[i], y[i])
            points.Add(point)
    return points

# Cut the airfoil.
def CutTrailingEdge(cutTEper):    
    f = cutTEper/100.0
    point = Point.Create(1-f*1.0,0.0,0.0)
    direction = Direction.Create(1,0,0)
	# Create a point.
    DatumPlaneCreator.Create(point,direction) 
    # Select the surface.
    selection = Selection.CreateByNames("Surface")
	# Select the plane.
    datum = Selection.CreateByNames("Plane")
	# Split body by plane.
    result = SplitBody.ByCutter(Selection.CreateByNames("Surface"), Selection.CreateByNames("Plane")) 
    # Select the smallest part.
    selection = Selection.CreateByNames("Surface") 
	# Remove the smallest part.
    result = Combine.RemoveRegions(selection) 
    return

# Update Airfoil, before Next button is pressed.
def UpdateAirfoil(step,property):
    # Get user inputs.
    Naca = step.Properties["Naca"].ValueString 
    Points = step.Properties["Points"].Value
    Preview = step.Properties["Preview"].ValueString
	
	# If user has selected show option, show the airfoil.
    if Preview == "Show":
        DeleteAllVisible()
	    
		# Set sketch mode.
        mode = InteractionMode.Sketch
        viewResult = ViewHelper.SetViewMode(mode)
        viewResult = ViewHelper.SetSketchPlane(Plane.PlaneXY)
	    
		# Convert user inputs to percentages.
        max_camb = float(Naca[0])/100.0
        max_camb_loc = float(Naca[1])/10.0
        thick_perc = float(Naca[2:4])/100.0	
	
        nx = Points/1.0
        dx = 1.0/nx
	
        x= range(0,Points+1,1)
        for i in range(0,len(x),1):
            x[i]=i*dx
	    
		# Create the points.
        (x,y) = CreateAirfoil(max_camb, max_camb_loc,thick_perc,x)
		# Save points in a list.
        points = Point2DList(x,y,True)
		
        # Create the curve.
        curve = SketchNurbs.CreateFrom2DPoints(False, points)
		# Set solid mode.
        mode = InteractionMode.Solid
        result = ViewHelper.SetViewMode(mode)
        
		# If cut trailing has selected, do it.
        if ShowCutValue(step,"Cut Trailing/CutTE") == True:
		    # Get user input value.
            CutValue = step.Properties["Cut Trailing/CutValue"].Value
            CutTrailingEdge(CutValue)
			
	    # Select Surface1.
        selection = Selection.CreateByNames("Surface1")
		# Activate Surface1.
        selection.SetActive()
		
	# If user has selected delete option, delete the airfoil.	
    elif Preview == "Delete":
	    DeleteAllVisible()
    return True

# Create a Fluid Flow Fluent system and define steps.	
def CreateFluent(step):
    # Create the system.
    template1 = GetTemplate(TemplateName="Fluid Flow")
    system1 = template1.CreateSystem()
    system1.DisplayText = "FFF"
	
	# Define with which system's component is associated each step.
    nextStep = step.NextStep
    if nextStep!=None:
        nextStep.SystemName = system1.Name
        nextStep.ComponentName = "Geometry"
        nextStep = nextStep.NextStep
    if nextStep!=None:
        nextStep.SystemName = system1.Name
        nextStep.ComponentName = "Geometry"
        nextStep = nextStep.NextStep
    if nextStep!=None:
        nextStep.SystemName = system1.Name
        nextStep.ComponentName = "Geometry"
        nextStep = nextStep.NextStep
    if nextStep!=None:
        nextStep.SystemName = system1.Name
        nextStep.ComponentName = "Mesh"

# Is called when Back button is pressed on 3rd step.
def DeleteAirfoil(step):
    selection = Selection.SelectAll()
    if selection.Items.Count > 0:
        result = Delete.Execute(selection)
    return

# Do scale, rotate and pull, before Next button is pressed.
def ScaleRotatePull(step,property):
    # Get user inputs.
    Chord = step.Properties["Chord"].Value
    Angle = step.Properties["Angle"].Value
    Angle = -Angle
    Preview2 = step.Properties["Preview2"].ValueString
	
	# If user has selected show option, do scale, rotate and pull.
    if Preview2 == "Show":
		
       # Scale
       CutTE = step.PreviousStep.Properties["Cut Trailing/CutTE"].ValueString
       if CutTE == "No":
	       selection = Selection.CreateByNames("Surface")
       else:
           selection = Selection.CreateByNames("Surface1")
		   
       preserveHoles = False
       if Chord != 0:
           result = Scale.Execute(selection, Frame.Create(Point.Create(MM(0), MM(0), MM(0)),Direction.DirX,Direction.DirY), Vector.Create(Chord,Chord,Chord), preserveHoles)
    
	   # Rotate
       if CutTE == "No":
	       selection = Selection.CreateByNames("Surface")
       else:
           selection = Selection.CreateByNames("Surface1")
       anchorPoint = Point.Create(M(0.25*Chord), M(0.0), M(0.0))
       axis = Line.Create(anchorPoint, Direction.DirZ)
       options = MoveOptions()
       options.CreatePatterns = False
       options.DetachFirst = False
       options.MaintainOrientation = False
       options.MaintainMirrorRelationships = True
       options.MaintainConnectivity = True
       options.MaintainOffsetRelationships = True
       options.Copy = False
       result = Move.Rotate(selection, axis, DEG(Angle), options)
	
	   # Pull, only if 3D mode has been selected.
       selection = step.PreviousStep.PreviousStep.Properties["2Dor3D"].ValueString
       if selection != "2D":
           WingSpan = step.Properties["WingSpan"].Value
           myBody = GetRootPart().Bodies[0]
           for myFace in myBody.Faces:
               selection = Selection.Create(myFace)
           options = ExtrudeFaceOptions()
           options.KeepMirror = True
           options.KeepLayoutSurfaces = False
           options.KeepCompositeFaceRelationships = True
           options.PullSymmetric = False
           options.OffsetMode = OffsetMode.IgnoreRelationships
           options.Copy = False
           options.ForceDoAsExtrude = False
           options.ExtrudeType = ExtrudeType.Add
           result = ExtrudeFaces.Execute(selection, M(WingSpan), options)
	
    # If user has selected delete option, delete scale, rotate and pull.	
    elif Preview2 == "Delete":
         SetAirfoil(step.PreviousStep)
         
    return True

# Is called when Next button is pressed at 2nd step.(Creates the airfoil)
def SetAirfoil(step):
    Naca = step.Properties["Naca"].ValueString
    Points = step.Properties["Points"].Value
    Preview = step.Properties["Preview"].ValueString
    DeleteAllVisible()
	
    mode = InteractionMode.Sketch
    viewResult = ViewHelper.SetViewMode(mode)
    viewResult = ViewHelper.SetSketchPlane(Plane.PlaneXY)
	
    max_camb = float(Naca[0])/100.0
    max_camb_loc = float(Naca[1])/10.0
    thick_perc = float(Naca[2:4])/100.0	
	
    nx = Points/1.0
    dx = 1.0/nx
	
    x= range(0,Points+1,1)
    for i in range(0,len(x),1):
        x[i]=i*dx
	
    (x,y) = CreateAirfoil(max_camb, max_camb_loc,thick_perc,x)
    points = Point2DList(x,y,True)
    
    curve = SketchNurbs.CreateFrom2DPoints(False, points)
    mode = InteractionMode.Solid
    result = ViewHelper.SetViewMode(mode)
    
    if ShowCutValue(step,"Cut Trailing/CutTE") == True:
        CutValue = step.Properties["Cut Trailing/CutValue"].Value
        CutTrailingEdge(CutValue)
	
    selection = Selection.CreateByNames("Surface1")
    selection.SetActive()
    return True

# Is called when Next Button is pressed at 3rd step.(Do scale,rotate and pull)
def SetScaleRotatePull(step):
    Chord = step.Properties["Chord"].Value
    Angle = step.Properties["Angle"].Value
    Angle = -Angle
    CutTE = step.PreviousStep.Properties["Cut Trailing/CutTE"].ValueString
    SetAirfoil(step.PreviousStep)
	
	# Exclude items from physics.
    selection = Selection.Create(GetRootPart().Curves)
    ViewHelper.SetSuppressForPhysics(selection, True)
	
	# Scale
    if CutTE == "No":
	    selection = Selection.CreateByNames("Surface")
    else:
        selection = Selection.CreateByNames("Surface1")
    preserveHoles = False
    if Chord != 0:
        result = Scale.Execute(selection, Frame.Create(Point.Create(MM(0), MM(0), MM(0)),Direction.DirX,Direction.DirY), Vector.Create(Chord,Chord,Chord), preserveHoles)
    
	# Rotate
    if CutTE == "No":
	    selection = Selection.CreateByNames("Surface")
    else:
        selection = Selection.CreateByNames("Surface1")
    anchorPoint = Point.Create(M(0.25*Chord), M(0.0), M(0.0))
    axis = Line.Create(anchorPoint, Direction.DirZ)
    options = MoveOptions()
    options.CreatePatterns = False
    options.DetachFirst = False
    options.MaintainOrientation = False
    options.MaintainMirrorRelationships = True
    options.MaintainConnectivity = True
    options.MaintainOffsetRelationships = True
    options.Copy = False
    result = Move.Rotate(selection, axis, DEG(Angle), options)
	
	# Pull, only if 3D mode has been selected.
    selection = step.PreviousStep.PreviousStep.Properties["2Dor3D"].ValueString
    if selection != "2D":
        WingSpan = step.Properties["WingSpan"].Value
        myBody = GetRootPart().Bodies[0]
        for myFace in myBody.Faces:
            selection = Selection.Create(myFace)
        options = ExtrudeFaceOptions()
        options.KeepMirror = True
        options.KeepLayoutSurfaces = False
        options.KeepCompositeFaceRelationships = True
        options.PullSymmetric = False
        options.OffsetMode = OffsetMode.IgnoreRelationships
        options.Copy = False
        options.ForceDoAsExtrude = False
        options.ExtrudeType = ExtrudeType.Add
        result = ExtrudeFaces.Execute(selection, M(WingSpan), options)
        Preview4 = "Delete"
		
		# Check if there is an old Enclosure component and delete it.
        try:
            myBody2 = GetRootPart().Components[0]
            selection = Selection.Create(myBody2)
            result = Delete.Execute(selection)
        except:
		    return
    return True

# Create a Domain rectangle.
def CreateDomain(step,property):
    # Get user inputs.
    RightX = step.Properties["2DDomain/RightX"].Value
    LeftX = step.Properties["2DDomain/LeftX"].Value
    UpY = step.Properties["2DDomain/UpY"].Value
    DownY = step.Properties["2DDomain/DownY"].Value
    Preview3 = step.Properties["2DDomain/Preview3"].ValueString
    CutTE = step.PreviousStep.PreviousStep.Properties["Cut Trailing/CutTE"].ValueString
	# If user has selected show option, show the 2D domain.
    if Preview3 == "Show":
	    # Set Sketch Plane.
        sectionPlane = Plane.PlaneXY
        result = ViewHelper.SetSketchPlane(sectionPlane)

        # Sketch Rectangle.
        point1 = Point2D.Create(M(LeftX),M(UpY))
        point2 = Point2D.Create(M(RightX),M(UpY))
        point3 = Point2D.Create(M(RightX),M(DownY))
        result = SketchRectangle.Create(point1, point2, point3)

        # Solidify Sketch.
        mode = InteractionMode.Solid
        result = ViewHelper.SetViewMode(mode)

        # Rename Objects.
        if CutTE == "No":
            selection = Selection.Create(GetRootPart().Bodies[0].Faces[0])
            result = Delete.Execute(selection)
        else:
		    # Delete Objects.
            selection = Selection.Create(GetRootPart().Bodies[0].Faces[0])
            result = Delete.Execute(selection)

        # Solidify Sketch.
        mode = InteractionMode.Solid
        result = ViewHelper.SetViewMode(mode)
    
	# If user has selected delete option, delete the 2D Domain.
    elif Preview3 == "Delete":
         SetScaleRotatePull(step.PreviousStep)

# Is called when Next Button is pressed at 4th step.(Creates the Domain or the Enclosure)	
def SetDomainOrEnclosure(step):
    CutTE = step.PreviousStep.PreviousStep.Properties["Cut Trailing/CutTE"].ValueString
	# Get first user input.
    selection = step.PreviousStep.PreviousStep.PreviousStep.Properties["2Dor3D"].ValueString
	
	# If user has selected 2D mode, create the 2D domain.
    if selection == "2D":
        RightX = step.Properties["2DDomain/RightX"].Value
        LeftX = step.Properties["2DDomain/LeftX"].Value
        UpY = step.Properties["2DDomain/UpY"].Value
        DownY = step.Properties["2DDomain/DownY"].Value
	
        SetScaleRotatePull(step.PreviousStep)
	    # Set Sketch Plane.
        sectionPlane = Plane.PlaneXY
        result = ViewHelper.SetSketchPlane(sectionPlane)

        # Sketch Rectangle.
        point1 = Point2D.Create(M(LeftX),M(UpY))
        point2 = Point2D.Create(M(RightX),M(UpY))
        point3 = Point2D.Create(M(RightX),M(DownY))
        result = SketchRectangle.Create(point1, point2, point3)

        # Solidify Sketch.
        mode = InteractionMode.Solid
        result = ViewHelper.SetViewMode(mode)

        # Delete Objects.
        if CutTE == "No":
            selection = Selection.Create(GetRootPart().Bodies[0].Faces[0])
            result = Delete.Execute(selection)
        else:
		    # Delete Objects.
            selection = Selection.Create(GetRootPart().Bodies[0].Faces[0])
            result = Delete.Execute(selection)

        # Solidify Sketch.
        mode = InteractionMode.Solid
        result = ViewHelper.SetViewMode(mode)
		
	# If user has selected 3D mode, create the 3D Enclosure.
    elif selection != "2D":
         RX = step.Properties["3DEnclosure/RX"].Value
         LX = step.Properties["3DEnclosure/LX"].Value
         UY = step.Properties["3DEnclosure/UY"].Value
         DY = step.Properties["3DEnclosure/DY"].Value
         FZ = step.Properties["3DEnclosure/FZ"].Value
		 
         SetScaleRotatePull(step.PreviousStep)
		 
		 # Check if there is an old Enclosure and delete it.
         try:
             myBody2 = GetRootPart().Components[0]
             selection = Selection.Create(myBody2)
             result = Delete.Execute(selection)
			 
             myBody = GetRootPart().Bodies[0]
             selection = Selection.Create(myBody)
             options = EnclosureOptions()
             options.EnclosureType = EnclosureType.Box
             options.EnclosureCushion = BoxEnclosureCushion(M(LX),M(RX),M(DY),M(UY),M(0),M(FZ))
             options.CustomBody = None
             options.CreateShareTopology = False
             options.Frame = Frame.Create(Point.Create(MM(0), MM(0), MM(0)),  Direction.DirX, Direction.DirY)
             options.CushionProportion = PERCENT(25)
             result = Enclosure.Create(selection, options)
			 
             selection = Selection.Create(myBody)
             result = Delete.Execute(selection)
         except:   
             myBody = GetRootPart().Bodies[0]
             selection = Selection.Create(myBody)
             options = EnclosureOptions()
             options.EnclosureType = EnclosureType.Box
             options.EnclosureCushion = BoxEnclosureCushion(M(LX),M(RX),M(DY),M(UY),M(0),M(FZ))
             options.CustomBody = None
             options.CreateShareTopology = False
             options.Frame = Frame.Create(Point.Create(MM(0), MM(0), MM(0)), Direction.DirX, Direction.DirY)
             options.CushionProportion = PERCENT(25)
             result = Enclosure.Create(selection, options)
			 
             if CutTE == "Yes":
                 selection = Selection.Create(myBody)
                 result = Delete.Execute(selection)
             else:
                 selection = Selection.Create(myBody)
                 result = Delete.Execute(selection)
		 # Create Named Selections for each face.
         for face in GetRootPart().Components[0].Content.Bodies[0].Faces:
            myNS = NamedSelection.Create(Selection.Create(face),Selection())
         
		 # Delete Objects.
         result = NamedSelection.Delete("Group1")
         result = NamedSelection.Delete("Group2")
         result = NamedSelection.Delete("Group3")
		 
		 # Rename Objects.
         result = NamedSelection.Rename("Group5", "Outlet")
         result = NamedSelection.Rename("Group7", "Inlet")
         result = NamedSelection.Rename("Group4", "Symmetry1")
         result = NamedSelection.Rename("Group8", "Symmetry2")
         result = NamedSelection.Rename("Group6", "Symmetry3")
         result = NamedSelection.Rename("Group9", "Symmetry4")
		 
		 # Create group of Named selections.
         primarySelection = Selection.Create(GetRootPart().Components[0].Content.Bodies[0].Faces[0],
         GetRootPart().Components[0].Content.Bodies[0].Faces[1],
         GetRootPart().Components[0].Content.Bodies[0].Faces[2])
         secondarySelection = Selection.Empty()
         result = NamedSelection.Create(primarySelection, secondarySelection)
		 
		 # Rename Object.
         result = NamedSelection.Rename("Group1", "Airfoil")

# Undo scale, rotate and pull.	
def DeleteScaleRotatePull(step):
    SetAirfoil(step.PreviousStep)

# Undo Domain or Enclosure creation.	
def DeleteDomainOrEnclosure(step):
    SetScaleRotatePull(step.PreviousStep)
    selection = step.PreviousStep.PreviousStep.PreviousStep.Properties["2Dor3D"].ValueString
    if selection != "2D":
        Preview4 = "Delete"

# Create an Enclosure and delete the inside solid(airfoil).
def CreateEnclosure(step,property):
    # Get user inputs.
    RX = step.Properties["3DEnclosure/RX"].Value
    LX = step.Properties["3DEnclosure/LX"].Value
    UY = step.Properties["3DEnclosure/UY"].Value
    DY = step.Properties["3DEnclosure/DY"].Value
    FZ = step.Properties["3DEnclosure/FZ"].Value
    Preview4 = step.Properties["3DEnclosure/Preview4"].ValueString
    CutTE = step.PreviousStep.PreviousStep.Properties["Cut Trailing/CutTE"].ValueString
	
	# If show option is selected, create the Enclosure.
    if Preview4 == "Show":
        myBody = GetRootPart().Bodies[0]
        selection = Selection.Create(myBody)

        options = EnclosureOptions()
        options.EnclosureType = EnclosureType.Box
        options.EnclosureCushion = BoxEnclosureCushion(M(LX),M(RX),M(DY),M(UY),M(0),M(FZ))
        options.CustomBody = None
        options.CreateShareTopology = False
        options.Frame = Frame.Create(Point.Create(MM(0), MM(0), MM(0)), 
        Direction.DirX, 
        Direction.DirY)
        options.CushionProportion = PERCENT(25)
        result = Enclosure.Create(selection, options)
        
		# Delete Objects.
        if CutTE == "Yes":
            selection = Selection.Create(myBody)
            result = Delete.Execute(selection)
        else:
            selection = Selection.Create(myBody)
            result = Delete.Execute(selection)
	# If delete option is selected, delete the Enclosure.	
    elif Preview4 == "Delete":
         SetScaleRotatePull(step.PreviousStep)
		 
		 # Check if there is an old component and delete it.
         try:
             myBody2 = GetRootPart().Components[0]
             selection = Selection.Create(myBody2)
             result = Delete.Execute(selection)
         except:
		     return
 
# Create Mesh.(Either 2D or 3D)
def CreateMesh(step):
    # Get user input.
    ElemSize = step.Properties["MeshControls/ElemSize"].Value
    
	# Communicate with Mechanical by sending a text with commands.
    commands = "model = ExtAPI.DataModel.Project.Model\n"
    commands += "mesh = model.Mesh\n"
	
    #commands += "sizing = mesh.AddSizing()\n"
    #commands += "ids = []\n"
	
    #selection = step.PreviousStep.PreviousStep.PreviousStep.PreviousStep.Properties["2Dor3D"].ValueString
    #if selection != "2D":
        #commands += "for part in ExtAPI.DataModel.GeoData.Assemblies[0].Parts:\n\tfor body in part.Bodies:\n\t\tids.Add(body.Id)\n"
    #elif selection == "2D":
	    #commands += "for part in ExtAPI.DataModel.GeoData.Assemblies[0].Parts:\n\tfor body in part.Bodies:\n\t\tfor face in body.Faces:\n\t\t\tids.Add(face.Id)\n"
    #commands += "sel = ExtAPI.SelectionManager.CreateSelectionInfo(SelectionTypeEnum.GeometryEntities)\n"
    #commands += "sel.Ids = ids\n"
    #commands += "sizing.Location = sel\n"
    #commands += "sizing.Type = SizingType.ElementSize\n"
	
    commands += "Elem =" +ElemSize.ToString()+"\n"
	
    #commands += "sizing.ElementSize = Quantity(Elem,'m')\n"
	
    commands += "mesh.ElementSize = Quantity(Elem,'m')\n"
    commands += "mesh.CaptureCurvature = True\n"
    commands += "mesh.CaptureProximity = True\n"
    commands += "mesh.Update()\n"
	
	# Send Commands to Mechanical and generate mesh.
    systems = GetAllSystems()
    system = systems[0]
    model = system.GetContainer(ComponentName="Mesh")
    model.Refresh()
    model.Edit()
    model.SendCommand(Language = "Python", Command = commands)
    model.Exit()
	
