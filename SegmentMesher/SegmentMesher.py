from __future__ import print_function
import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging

#
# SegmentMesher
#

class SegmentMesher(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Segment Mesher"
    self.parent.categories = ["Segmentation"]
    self.parent.dependencies = []
    self.parent.contributors = ["Andras Lasso (PerkLab - Queen's University)"]
    self.parent.helpText = """Create volumetric mesh consisting of tetrahedral elements using Cleaver2 or TetGen meshers.
<p>See <a href="https://github.com/lassoan/SlicerSegmentMesher/blob/master/README.md">module documentation</a> for description of meshing parameters.
<p><a href="https://sciinstitute.github.io/cleaver.pages">Cleaver2</a> is freely usable, without any restrictions.
<p><a href="http://www.tetgen.org">TetGen<a> is only free for private, research, and educational use (see <a href="https://people.sc.fsu.edu/~jburkardt/examples/tetgen/license.txt">license</a> for details).
"""
    #self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
This module was originally developed by Andras Lasso (Queen's University, PerkLab) to serve as a convenient frontend for existing commonly used open-source generator software.

<p>Cleaver is an Open Source software project that is principally funded through the SCI Institute's NIH/NIGMS CIBC Center. Please use the following acknowledgment and send references to any publications, presentations, or successful funding applications that make use of NIH/NIGMS CIBC software or data sets to <a href="http://www.sci.utah.edu/software/cleaver.html">SCI</a>: "This project was supported by the National Institute of General Medical Sciences of the National Institutes of Health under grant number P41 GM103545-18."

<p>TetGen citation: Si, Hang (2015). "TetGen, a Delaunay-based Tetrahedral Mesh Generator". ACM Transactions on Mathematical Software. 41 (2): 11:1-11:36. doi:10.1145/2629697
"""

#
# SegmentMesherWidget
#

class SegmentMesherWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    self.logic = SegmentMesherLogic()
    self.logic.logCallback = self.addLog
    self.modelGenerationInProgress = False

    uiWidget = slicer.util.loadUI(self.resourcePath('UI/SegmentMesher.ui'))
    self.layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)
    uiWidget.setPalette(slicer.util.mainWindow().style().standardPalette())

    # Finish UI setup ...    
    self.ui.parameterNodeSelector.addAttribute( "vtkMRMLScriptedModuleNode", "ModuleName", "SegmentMesher" )    
    self.ui.parameterNodeSelector.setMRMLScene( slicer.mrmlScene )    
    self.ui.inputModelSelector.setMRMLScene( slicer.mrmlScene )    
    self.ui.inputSurfaceSelector.setMRMLScene( slicer.mrmlScene )
    self.ui.outputModelSelector.setMRMLScene( slicer.mrmlScene )

    self.ui.methodSelectorComboBox.addItem("Cleaver", METHOD_CLEAVER)
    self.ui.methodSelectorComboBox.addItem("TetGen", METHOD_TETGEN)    

    customCleaverPath = self.logic.getCustomCleaverPath()
    self.ui.customCleaverPathSelector.setCurrentPath(customCleaverPath)
    self.ui.customCleaverPathSelector.nameFilters = [self.logic.cleaverFilename]    

    customTetGenPath = self.logic.getCustomTetGenPath()
    self.ui.customTetGenPathSelector.setCurrentPath(customTetGenPath)
    self.ui.customTetGenPathSelector.nameFilters = [self.logic.tetGenFilename]
   
    clipNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLClipModelsNode")
    self.ui.clipNodeWidget.setMRMLClipNode(clipNode)
    

    # connections
    self.ui.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.ui.showTemporaryFilesFolderButton.connect('clicked(bool)', self.onShowTemporaryFilesFolder)
    self.ui.inputModelSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateMRMLFromGUI)
    self.ui.inputSurfaceSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateMRMLFromGUI)
    self.ui.outputModelSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateMRMLFromGUI)
    self.ui.methodSelectorComboBox.connect("currentIndexChanged(int)", self.updateMRMLFromGUI)
    # Immediately update deleteTemporaryFiles in the logic to make it possible to decide to
    # keep the temporary file while the model generation is running
    self.ui.keepTemporaryFilesCheckBox.connect("toggled(bool)", self.onKeepTemporaryFilesToggled)
    self.ui.tetgenUseSurface.connect("toggled(bool)", self.updateMRMLFromGUI)

    # Add vertical spacer
    self.layout.addStretch(1)

    # Refresh Apply button state
    self.updateMRMLFromGUI()

  def enter(self):
    self.updateMRMLFromGUI()
  
  def cleanup(self):
    pass

   
  def updateMRMLFromGUI(self):
    
    method = self.ui.methodSelectorComboBox.itemData(self.ui.methodSelectorComboBox.currentIndex)
    
    #Enable correct input selections
    self.ui.inputSurfaceSelector.enabled = self.ui.tetgenUseSurface.isChecked() and method == METHOD_TETGEN
    self.ui.segmentSelectorCombBox.enabled = not (self.ui.tetgenUseSurface.isChecked() and method == METHOD_TETGEN) and self.ui.inputModelSelector.currentNode() is not None
    self.ui.inputModelSelector.enabled = not (self.ui.tetgenUseSurface.isChecked() and method == METHOD_TETGEN)

    #populate segments 
    inputSeg = self.ui.inputModelSelector.currentNode()
    oldIndex = self.ui.segmentSelectorCombBox.checkedIndexes()
    oldCount = self.ui.segmentSelectorCombBox.count
    self.ui.segmentSelectorCombBox.clear()
    if inputSeg is not None:
      segmentIDs = vtk.vtkStringArray()
      inputSeg.GetSegmentation().GetSegmentIDs(segmentIDs) 
      for index in range(0, segmentIDs.GetNumberOfValues()):
        self.ui.segmentSelectorCombBox.addItem(segmentIDs.GetValue(index))

    #Restore index - often we will be reloading the data from the same segmentation, so re-select items number of items is the same
    if oldCount == self.ui.segmentSelectorCombBox.count:
      for index in oldIndex:
        self.ui.segmentSelectorCombBox.setCheckState(index, qt.Qt.Checked)
    
    if method == METHOD_TETGEN:
      self.ui.advancedTabWidget.setCurrentWidget(self.ui.tetgenTab)
      self.ui.advancedTabWidget.setTabEnabled( self.ui.advancedTabWidget.indexOf(self.ui.cleaverTab), False)
      self.ui.advancedTabWidget.setTabEnabled( self.ui.advancedTabWidget.indexOf(self.ui.tetgenTab), True)      
      self.ui.advancedTabWidget.setStyleSheet("QTabBar::tab::disabled {width: 0; height: 0; margin: 0; padding: 0; border: none;} ")

    if method == METHOD_CLEAVER:
      self.ui.advancedTabWidget.setCurrentWidget(self.ui.cleaverTab)
      self.ui.advancedTabWidget.setTabEnabled( self.ui.advancedTabWidget.indexOf(self.ui.tetgenTab), False)
      self.ui.advancedTabWidget.setTabEnabled( self.ui.advancedTabWidget.indexOf(self.ui.cleaverTab), True)
      self.ui.advancedTabWidget.setStyleSheet("QTabBar::tab::disabled {width: 0; height: 0; margin: 0; padding: 0; border: none;} ")
    
    if method == METHOD_TETGEN and self.ui.tetgenUseSurface.isChecked():
      if not self.ui.inputSurfaceSelector.currentNode():
        self.ui.applyButton.text = "Select input surface"
        self.ui.applyButton.enabled = False
      elif not self.ui.outputModelSelector.currentNode():
        self.ui.applyButton.text = "Select an output model node"
        self.ui.applyButton.enabled = False
      elif self.ui.inputSurfaceSelector.currentNode() == self.ui.outputModelSelector.currentNode():
        self.ui.applyButton.text = "Choose different Output model"
        self.ui.applyButton.enabled = False
      else:
        self.ui.applyButton.text = "Apply"
        self.ui.applyButton.enabled = True
    else:
      if not self.ui.inputModelSelector.currentNode():
        self.ui.applyButton.text = "Select input segmentation"
        self.ui.applyButton.enabled = False
      elif not self.ui.outputModelSelector.currentNode():
        self.ui.applyButton.text = "Select an output model node"
        self.ui.applyButton.enabled = False
      elif self.ui.inputModelSelector.currentNode() == self.ui.outputModelSelector.currentNode():
        self.ui.applyButton.text = "Choose different Output model"
        self.ui.applyButton.enabled = False
      else:
        self.ui.applyButton.text = "Apply"
        self.ui.applyButton.enabled = True

  # def updateGUIFromMRML(self):
    # parameterNode = self.parameterNodeSelector.currentNode()
    # method = parameterNode.parameter("Method")
    # methodIndex = self.methodSelectorComboBox.findData(method)
    # wasBlocked = self.methodSelectorComboBox.blockSignals(True)
    # self.methodSelectorComboBox.setCurrentIndex(methodIndex)
    # self.methodSelectorComboBox.blockSignals(wasBlocked)

  def onShowTemporaryFilesFolder(self):
    qt.QDesktopServices().openUrl(qt.QUrl("file:///" + self.logic.getTempDirectoryBase(), qt.QUrl.TolerantMode));

  def onKeepTemporaryFilesToggled(self, toggle):
    self.logic.deleteTemporaryFiles = toggle

  def onApplyButton(self):
    if self.modelGenerationInProgress:
      self.modelGenerationInProgress = False
      self.logic.abortRequested = True
      self.ui.applyButton.text = "Cancelling..."
      self.ui.applyButton.enabled = False
      return

    self.modelGenerationInProgress = True
    self.ui.applyButton.text = "Cancel"
    self.ui.statusLabel.plainText = ''
    slicer.app.setOverrideCursor(qt.Qt.WaitCursor)
    try:
      self.logic.setCustomCleaverPath(self.ui.customCleaverPathSelector.currentPath)
      self.logic.setCustomTetGenPath(self.ui.customTetGenPathSelector.currentPath)

      self.logic.deleteTemporaryFiles = not self.ui.keepTemporaryFilesCheckBox.checked
      self.logic.logStandardOutput = self.ui.showDetailedLogDuringExecutionCheckBox.checked

      method = self.ui.methodSelectorComboBox.itemData(self.ui.methodSelectorComboBox.currentIndex)

      #Get list of segments to mesh
      segmentIndexes = self.ui.segmentSelectorCombBox.checkedIndexes()
      segments = []

      for index in segmentIndexes:
        segments.append(self.ui.segmentSelectorCombBox.itemText(index.row()))

      print(method)
      if method == METHOD_CLEAVER:
        self.logic.createMeshFromSegmentationCleaver(self.ui.inputModelSelector.currentNode(),
          self.ui.outputModelSelector.currentNode(), segments, self.ui.cleaverAdditionalParametersWidget.text,
          self.ui.cleaverRemoveBackgroundMeshCheckBox.isChecked(),
          self.ui.cleaverPaddingPercentSpinBox.value * 0.01, self.ui.cleaverScaleParameterWidget.value, self.ui.cleaverMultiplierParameterWidget.value, self.ui.cleaverGradingParameterWidget.value)
      else:
        if self.ui.tetgenUseSurface.isChecked():
          if self.ui.inputSurfaceSelector.currentNode().GetUnstructuredGrid() is not None:
            self.addLog("Error: Mesh must be a surface, not volumetric")
            return
          self.logic.createMeshFromPolyDataTetGen(self.ui.inputSurfaceSelector.currentNode().GetPolyData(), 
            self.ui.outputModelSelector.currentNode(), self.ui.tetGenAdditionalParametersWidget.text,
            self.ui.tetgenRatioParameterWidget.value, self.ui.tetgenAngleParameterWidget.value, self.ui.tetgenVolumeParameterWidget.value)
        else:
          self.logic.createMeshFromSegmentationTetGen(self.ui.inputModelSelector.currentNode(),
            self.ui.outputModelSelector.currentNode(), segments, self.ui.tetGenAdditionalParametersWidget.text,
            self.ui.tetgenRatioParameterWidget.value, self.ui.tetgenAngleParameterWidget.value, self.ui.tetgenVolumeParameterWidget.value)

    except Exception as e:
      print(e)
      self.addLog("Error: {0}".format(str(e)))
      import traceback
      traceback.print_exc()
    finally:
      slicer.app.restoreOverrideCursor()
      self.modelGenerationInProgress = False
      self.updateMRMLFromGUI() # restores default Apply button state

  def addLog(self, text):
    """Append text to log window
    """
    self.ui.statusLabel.appendPlainText(text)
    slicer.app.processEvents()  # force update

#
# SegmentMesherLogic
#

class SegmentMesherLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self):
    ScriptedLoadableModuleLogic.__init__(self)
    self.logCallback = None
    self.abortRequested = False
    self.deleteTemporaryFiles = True
    self.logStandardOutput = False
    self.customCleaverPathSettingsKey = 'SegmentMesher/CustomCleaverPath'
    self.customTetGenPathSettingsKey = 'SegmentMesher/CustomTetGenPath'
    import os
    self.scriptPath = os.path.dirname(os.path.abspath(__file__))
    self.cleaverPath = None # this will be determined dynamically
    self.tetGenPath = None # this will be determined dynamically

    import platform
    executableExt = '.exe' if platform.system() == 'Windows' else ''
    self.cleaverFilename = 'cleaver-cli' + executableExt
    self.tetGenFilename = 'tetgen' + executableExt

    self.binDirCandidates = [
      # install tree
      os.path.join(self.scriptPath, '..'),
      os.path.join(self.scriptPath, '../../../bin'),
      # build tree
      os.path.join(self.scriptPath, '../../../../bin'),
      os.path.join(self.scriptPath, '../../../../bin/Release'),
      os.path.join(self.scriptPath, '../../../../bin/Debug'),
      os.path.join(self.scriptPath, '../../../../bin/RelWithDebInfo'),
      os.path.join(self.scriptPath, '../../../../bin/MinSizeRel') ]

  def addLog(self, text):
    logging.info(text)
    if self.logCallback:
      self.logCallback(text)

  def getCleaverPath(self):
    if self.cleaverPath:
      return self.cleaverPath

    self.cleaverPath = self.getCustomCleaverPath()
    if self.cleaverPath:
      return self.cleaverPath

    for binDirCandidate in self.binDirCandidates:
      cleaverPath = os.path.abspath(os.path.join(binDirCandidate, self.cleaverFilename))
      logging.debug("Attempt to find executable at: "+cleaverPath)
      if os.path.isfile(cleaverPath):
        # found
        self.cleaverPath = cleaverPath
        return self.cleaverPath

    raise ValueError('Cleaver not found')

  def getTetGenPath(self):
    if self.tetGenPath:
      return self.tetGenPath

    self.tetGenPath = self.getCustomTetGenPath()
    if self.tetGenPath:
      return self.tetGenPath

    for tetGenBinDirCandidate in self.binDirCandidates:
      tetGenPath = os.path.abspath(os.path.join(tetGenBinDirCandidate, self.tetGenFilename))
      logging.debug("Attempt to find executable at: "+tetGenPath)
      if os.path.isfile(tetGenPath):
        # TetGen found
        self.tetGenPath = tetGenPath
        return self.tetGenPath

    raise ValueError('TetGen not found')

  def getCustomCleaverPath(self):
    settings = qt.QSettings()
    if settings.contains(self.customCleaverPathSettingsKey):
      return settings.value(self.customCleaverPathSettingsKey)
    return ''

  def getCustomTetGenPath(self):
    settings = qt.QSettings()
    if settings.contains(self.customTetGenPathSettingsKey):
      return settings.value(self.customTetGenPathSettingsKey)
    return ''

  def setCustomCleaverPath(self, customPath):
    # don't save it if already saved
    settings = qt.QSettings()
    if settings.contains(self.customCleaverPathSettingsKey):
      if customPath == settings.value(self.customCleaverPathSettingsKey):
        return
    settings.setValue(self.customCleaverPathSettingsKey, customPath)
    # Update Cleaver bin dir
    self.cleaverPath = None
    self.getCleaverPath()

  def setCustomTetGenPath(self, customPath):
    # don't save it if already saved
    settings = qt.QSettings()
    if settings.contains(self.customTetGenPathSettingsKey):
      if customPath == settings.value(self.customTetGenPathSettingsKey):
        return
    settings.setValue(self.customTetGenPathSettingsKey, customPath)
    # Update TetGen bin dir
    self.tetGenPath = None
    self.getTetGenPath()

  def startMesher(self, cmdLineArguments, executableFilePath):
    self.addLog("Generating volumetric mesh...")
    import subprocess

    # Hide console window on Windows
    from sys import platform
    if platform == "win32":
      info = subprocess.STARTUPINFO()
      info.dwFlags = 1
      info.wShowWindow = 0
    else:
      info = None

    logging.info("Generate mesh using: "+executableFilePath+": "+repr(cmdLineArguments))
    return subprocess.Popen([executableFilePath] + cmdLineArguments,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, startupinfo=info)

  def logProcessOutput(self, process, processName):
    # save process output (if not logged) so that it can be displayed in case of an error
    processOutput = ''
    import subprocess
    for stdout_line in iter(process.stdout.readline, ""):
      if self.logStandardOutput:
        self.addLog(stdout_line.rstrip())
      else:
        processOutput += stdout_line.rstrip() + '\n'
      slicer.app.processEvents()  # give a chance to click Cancel button
      if self.abortRequested:
        process.kill()
    process.stdout.close()
    return_code = process.wait()
    if return_code:
      if self.abortRequested:
        raise ValueError("User requested cancel.")
      else:
        if processOutput:
          self.addLog(processOutput)
        raise subprocess.CalledProcessError(return_code, processName)

  def getTempDirectoryBase(self):
    tempDir = qt.QDir(slicer.app.temporaryPath)
    fileInfo = qt.QFileInfo(qt.QDir(tempDir), "SegmentMesher")
    dirPath = fileInfo.absoluteFilePath()
    qt.QDir().mkpath(dirPath)
    return dirPath

  def createTempDirectory(self):
    import qt, slicer
    tempDir = qt.QDir(self.getTempDirectoryBase())
    tempDirName = qt.QDateTime().currentDateTime().toString("yyyyMMdd_hhmmss_zzz")
    fileInfo = qt.QFileInfo(qt.QDir(tempDir), tempDirName)
    dirPath = fileInfo.absoluteFilePath()
    qt.QDir().mkpath(dirPath)
    return dirPath

  def createMeshFromSegmentationCleaver(self, inputSegmentation, outputMeshNode, segments = [], additionalParameters = None, removeBackgroundMesh = False, paddingRatio = 0.10, scale = 0.2, multiplier=0.5, grading=1.0):

    if additionalParameters is None:
      additionalParameters=""


    self.abortRequested = False
    tempDir = self.createTempDirectory()
    self.addLog('Mesh generation using Cleaver is started in working directory: '+tempDir)

    inputParamsCleaver = []

    # Write inputs
    qt.QDir().mkpath(tempDir)

    # Create temporary labelmap node. It will be used both for storing reference geometry
    # and resulting merged labelmap.
    labelmapVolumeNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLabelMapVolumeNode')
    parentTransformNode  = inputSegmentation.GetParentTransformNode()
    labelmapVolumeNode.SetAndObserveTransformNodeID(parentTransformNode.GetID() if parentTransformNode else None)

    # Create binary labelmap representation using default parameters
    if not inputSegmentation.GetSegmentation().CreateRepresentation(slicer.vtkSegmentationConverter.GetSegmentationBinaryLabelmapRepresentationName()):
      self.addLog('Failed to create binary labelmap representation')
      return

    # Set reference geometry in labelmapVolumeNode
    referenceGeometry_Segmentation = slicer.vtkOrientedImageData()
    inputSegmentation.GetSegmentation().SetImageGeometryFromCommonLabelmapGeometry(referenceGeometry_Segmentation, None,
      slicer.vtkSegmentation.EXTENT_REFERENCE_GEOMETRY)
    slicer.modules.segmentations.logic().CopyOrientedImageDataToVolumeNode(referenceGeometry_Segmentation, labelmapVolumeNode)

    # Add margin
    extent = labelmapVolumeNode.GetImageData().GetExtent()
    paddedExtent = [0, -1, 0, -1, 0, -1]
    for axisIndex in range(3):
      paddingSizeVoxels = int((extent[axisIndex * 2 + 1] - extent[axisIndex * 2]) * paddingRatio)
      paddedExtent[axisIndex * 2] = extent[axisIndex * 2] - paddingSizeVoxels
      paddedExtent[axisIndex * 2 + 1] = extent[axisIndex * 2 + 1] + paddingSizeVoxels
    labelmapVolumeNode.GetImageData().SetExtent(paddedExtent)
    labelmapVolumeNode.ShiftImageDataExtentToZeroStart()

    # Get merged labelmap
    segmentIdList = vtk.vtkStringArray()
    
    for segment in segments:
      segmentIdList.InsertNextValue(segment)

    if segmentIdList.GetNumberOfValues() == 0:
      logging.info("createMeshFromSegmentationCleaver skipped: there are no selected segments")
      return
      
    slicer.modules.segmentations.logic().ExportSegmentsToLabelmapNode(inputSegmentation, segmentIdList, labelmapVolumeNode, labelmapVolumeNode)
    

    inputLabelmapVolumeFilePath = os.path.join(tempDir, "inputLabelmap.nrrd")
    slicer.util.saveNode(labelmapVolumeNode, inputLabelmapVolumeFilePath, {"useCompression": False})
    inputParamsCleaver.extend(["--input_files", inputLabelmapVolumeFilePath])

    # Keep IJK to RAS matrix, we'll need it later
    unscaledIjkToRasMatrix = vtk.vtkMatrix4x4()
    labelmapVolumeNode.GetIJKToRASDirectionMatrix(unscaledIjkToRasMatrix)
    origin = labelmapVolumeNode.GetOrigin()
    for i in range(3):
      unscaledIjkToRasMatrix.SetElement(i,3, origin[i])

    # Keep color node, we'll need it later
    colorTableNode = labelmapVolumeNode.GetDisplayNode().GetColorNode()
    # Background color is transparent by default which is not ideal for 3D display
    colorTableNode.SetColor(0,0.6,0.6,0.6,1.0)

    slicer.mrmlScene.RemoveNode(labelmapVolumeNode)
    slicer.mrmlScene.RemoveNode(colorTableNode)

    #User set parameters
    inputParamsCleaver.extend(["--scale", str(scale)])
    inputParamsCleaver.extend(["--multiplier", str(multiplier)])
    inputParamsCleaver.extend(["--grading", str(grading)])
    
    # Set up output format

    inputParamsCleaver.extend(["--output_path", tempDir+"/"])
    inputParamsCleaver.extend(["--output_format", "vtkUSG"]) # VTK unstructed grid
    inputParamsCleaver.append("--fix_tet_windup") # prevent inside-out tets
    inputParamsCleaver.append("--strip_exterior") # remove temporary elements that are added to make the volume cubic

    inputParamsCleaver.append("--verbose")

    # Quality
    inputParamsCleaver.extend(additionalParameters.split(' '))

    # Run Cleaver
    ep = self.startMesher(inputParamsCleaver, self.getCleaverPath())
    self.logProcessOutput(ep, self.cleaverFilename)

    # Read results
    if not self.abortRequested:
      outputVolumetricMeshPath = os.path.join(tempDir, "output.vtk")
      outputReader = vtk.vtkUnstructuredGridReader()
      outputReader.SetFileName(outputVolumetricMeshPath)
      outputReader.ReadAllScalarsOn()
      outputReader.ReadAllVectorsOn()
      outputReader.ReadAllNormalsOn()
      outputReader.ReadAllTensorsOn()
      outputReader.ReadAllColorScalarsOn()
      outputReader.ReadAllTCoordsOn()
      outputReader.ReadAllFieldsOn()
      outputReader.Update()

      # Cleaver returns the mesh in voxel coordinates, need to transform to RAS space
      transformer = vtk.vtkTransformFilter()
      transformer.SetInputData(outputReader.GetOutput())
      ijkToRasTransform = vtk.vtkTransform()
      ijkToRasTransform.SetMatrix(unscaledIjkToRasMatrix)
      transformer.SetTransform(ijkToRasTransform)

      if removeBackgroundMesh:
        transformer.Update()
        mesh = transformer.GetOutput()
        cellData = mesh.GetCellData()
        cellData.SetActiveScalars("labels")
        backgroundMeshRemover = vtk.vtkThreshold()
        backgroundMeshRemover.SetInputData(mesh)
        backgroundMeshRemover.SetInputArrayToProcess(0, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_CELLS, vtk.vtkDataSetAttributes.SCALARS)
        backgroundMeshRemover.ThresholdByUpper(1)
        outputMeshNode.SetUnstructuredGridConnection(backgroundMeshRemover.GetOutputPort())
      else:
        outputMeshNode.SetUnstructuredGridConnection(transformer.GetOutputPort())

      outputMeshDisplayNode = outputMeshNode.GetDisplayNode()
      if not outputMeshDisplayNode:
        # Initial setup of display node
        outputMeshNode.CreateDefaultDisplayNodes()

        outputMeshDisplayNode = outputMeshNode.GetDisplayNode()
        outputMeshDisplayNode.SetEdgeVisibility(True)
        outputMeshDisplayNode.SetClipping(True)

        colorTableNode = slicer.mrmlScene.AddNode(colorTableNode)
        outputMeshDisplayNode.SetAndObserveColorNodeID(colorTableNode.GetID())

        outputMeshDisplayNode.ScalarVisibilityOn()
        outputMeshDisplayNode.SetActiveScalarName('labels')
        outputMeshDisplayNode.SetActiveAttributeLocation(vtk.vtkAssignAttribute.CELL_DATA)
        outputMeshDisplayNode.SetSliceIntersectionVisibility(True)
        outputMeshDisplayNode.SetSliceIntersectionOpacity(0.5)
        outputMeshDisplayNode.SetScalarRangeFlag(slicer.vtkMRMLDisplayNode.UseColorNodeScalarRange)
      else:
        currentColorNode = outputMeshDisplayNode.GetColorNode()
        if currentColorNode is not None and currentColorNode.GetType() == currentColorNode.User and currentColorNode.IsA("vtkMRMLColorTableNode"):
          # current color table node can be overwritten
          currentColorNode.Copy(colorTableNode)
        else:
          colorTableNode = slicer.mrmlScene.AddNode(colorTableNode)
          outputMeshDisplayNode.SetAndObserveColorNodeID(colorTableNode.GetID())

      # Flip clipping setting twice, this workaround forces update of the display pipeline
      # when switching between surface and volumetric mesh
      outputMeshDisplayNode.SetClipping(not outputMeshDisplayNode.GetClipping())
      outputMeshDisplayNode.SetClipping(not outputMeshDisplayNode.GetClipping())

    # Clean up
    if self.deleteTemporaryFiles:
      import shutil
      shutil.rmtree(tempDir)

    self.addLog("Model generation is completed")

  def createMeshFromSegmentationTetGen(self, inputSegmentation, outputMeshNode, segments = [], additionalParameters="", ratio=5, angle=0, volume=10):
    
    segmentIdList = vtk.vtkStringArray()    
    for segment in segments:
      segmentIdList.InsertNextValue(segment)

    if segmentIdList.GetNumberOfValues() == 0:
      logging.info("createMeshFromSegmentationTetGen skipped: there are no selected segments")
      return
    inputSegmentation.CreateClosedSurfaceRepresentation()
    appender = vtk.vtkAppendPolyData()
    for i in range(segmentIdList.GetNumberOfValues()):
      segmentId = segmentIdList.GetValue(i)

      #Use old function arguments for 4.10 
      if slicer.app.majorVersion == 4 and slicer.app.minorVersion < 11:
      	polydata = inputSegmentation.GetClosedSurfaceRepresentation(segmentId)      	      	
      else:
      	polydata = vtk.vtkPolyData()
      	inputSegmentation.GetClosedSurfaceRepresentation(segmentId, polydata)
      appender.AddInputData(polydata)

    appender.Update()
    self.createMeshFromPolyDataTetGen(appender.GetOutput(), outputMeshNode, additionalParameters, ratio, angle, volume)

    #Clean up representation
    inputSegmentation.GetSegmentation().RemoveRepresentation(slicer.vtkSegmentationConverter().GetClosedSurfaceRepresentationName())

  def createMeshFromPolyDataTetGen(self, inputPolyData, outputMeshNode, additionalParameters="", ratio=5, angle=0, volume=10):

    self.abortRequested = False
    tempDir = self.createTempDirectory()
    self.addLog('Mesh generation is started in working directory: '+tempDir)

    # Write inputs
    qt.QDir().mkpath(tempDir)

    inputSurfaceMeshFilePath = os.path.join(tempDir, "mesh.ply")
    inputWriter = vtk.vtkPLYWriter()
    inputWriter.SetInputData(inputPolyData)
    inputWriter.SetFileName(inputSurfaceMeshFilePath)
    inputWriter.SetFileTypeToASCII()
    inputWriter.Write()

    #Command line for quality parameters
    parameters = 'q'+str(ratio)+'/'+str(angle)+'a'+str(volume)

    inputParamsTetGen = []
    inputParamsTetGen.append("-k"+parameters+additionalParameters)
    inputParamsTetGen.append(inputSurfaceMeshFilePath)

    # Run tetgen
    ep = self.startMesher(inputParamsTetGen, self.getTetGenPath())
    self.logProcessOutput(ep, self.tetGenFilename)

    # Read results
    if not self.abortRequested:
      outputVolumetricMeshPath = os.path.join(tempDir, "mesh.1.vtk")
      outputReader = vtk.vtkUnstructuredGridReader()
      outputReader.SetFileName(outputVolumetricMeshPath)
      outputReader.ReadAllScalarsOn()
      outputReader.ReadAllVectorsOn()
      outputReader.ReadAllNormalsOn()
      outputReader.ReadAllTensorsOn()
      outputReader.ReadAllColorScalarsOn()
      outputReader.ReadAllTCoordsOn()
      outputReader.ReadAllFieldsOn()
      outputReader.Update()
      outputMeshNode.SetUnstructuredGridConnection(outputReader.GetOutputPort())

      outputMeshDisplayNode = outputMeshNode.GetDisplayNode()
      if not outputMeshDisplayNode:
        # Initial setup of display node
        outputMeshNode.CreateDefaultDisplayNodes()
        outputMeshDisplayNode = outputMeshNode.GetDisplayNode()
        outputMeshDisplayNode.SetEdgeVisibility(True)
        outputMeshDisplayNode.SetClipping(True)

    # Clean up
    if self.deleteTemporaryFiles:
      import shutil
      shutil.rmtree(tempDir)

    self.addLog("Model generation is completed")

class SegmentMesherTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_TetGen1()

  def test_TetGen1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")

    cylinder = vtk.vtkCylinderSource()
    cylinder.SetRadius(10)
    cylinder.SetHeight(40)
    cylinder.Update()
    inputModelNode = slicer.modules.models.logic().AddModel(cylinder.GetOutput())

    outputModelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode")
    outputModelNode.CreateDefaultDisplayNodes()

    logic = SegmentMesherLogic()
    logic.createMeshFromPolyDataTetGen(inputModelNode.GetPolyData(), outputModelNode, '', 100, 0, 100)

    self.assertTrue(outputModelNode.GetMesh().GetNumberOfPoints()>0)
    self.assertTrue(outputModelNode.GetMesh().GetNumberOfCells()>0)

    inputModelNode.GetDisplayNode().SetOpacity(0.2)

    outputDisplayNode = outputModelNode.GetDisplayNode()
    outputDisplayNode.SetColor(1,0,0)
    outputDisplayNode.SetEdgeVisibility(True)
    outputDisplayNode.SetClipping(True)

    clipNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLClipModelsNode")
    clipNode.SetRedSliceClipState(clipNode.ClipNegativeSpace)

    self.delayDisplay('Test passed!')

METHOD_CLEAVER = 'CLEAVER'
METHOD_TETGEN = 'TETGEN'
