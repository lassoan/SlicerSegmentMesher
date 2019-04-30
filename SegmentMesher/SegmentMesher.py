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

    # Instantiate and connect widgets ...

    # Parameter sets
    defaultinputParametersCollapsibleButton = ctk.ctkCollapsibleButton()
    defaultinputParametersCollapsibleButton.text = "Parameter set"
    defaultinputParametersCollapsibleButton.collapsed = True
    self.layout.addWidget(defaultinputParametersCollapsibleButton)
    defaultParametersLayout = qt.QFormLayout(defaultinputParametersCollapsibleButton)

    self.parameterNodeSelector = slicer.qMRMLNodeComboBox()
    self.parameterNodeSelector.nodeTypes = ["vtkMRMLScriptedModuleNode"]
    self.parameterNodeSelector.addAttribute( "vtkMRMLScriptedModuleNode", "ModuleName", "SegmentMesher" )
    self.parameterNodeSelector.selectNodeUponCreation = True
    self.parameterNodeSelector.addEnabled = True
    self.parameterNodeSelector.renameEnabled = True
    self.parameterNodeSelector.removeEnabled = True
    self.parameterNodeSelector.noneEnabled = False
    self.parameterNodeSelector.showHidden = True
    self.parameterNodeSelector.showChildNodeTypes = False
    self.parameterNodeSelector.baseName = "SegmentMesher"
    self.parameterNodeSelector.setMRMLScene( slicer.mrmlScene )
    self.parameterNodeSelector.setToolTip( "Pick parameter set" )
    defaultParametersLayout.addRow("Parameter set: ", self.parameterNodeSelector)

    #
    # Inputs
    #
    inputParametersCollapsibleButton = ctk.ctkCollapsibleButton()
    inputParametersCollapsibleButton.text = "Inputs"
    self.layout.addWidget(inputParametersCollapsibleButton)

    # Layout within the dummy collapsible button
    inputParametersFormLayout = qt.QFormLayout(inputParametersCollapsibleButton)

    self.inputModelSelector = slicer.qMRMLNodeComboBox()
    self.inputModelSelector.nodeTypes = ["vtkMRMLSegmentationNode"]
    self.inputModelSelector.selectNodeUponCreation = True
    self.inputModelSelector.addEnabled = False
    self.inputModelSelector.removeEnabled = False
    self.inputModelSelector.noneEnabled = False
    self.inputModelSelector.showHidden = False
    self.inputModelSelector.showChildNodeTypes = False
    self.inputModelSelector.setMRMLScene( slicer.mrmlScene )
    self.inputModelSelector.setToolTip( "Volumetric mesh will be generated for all visible segments in this segmentation node." )
    inputParametersFormLayout.addRow("Input segmentation: ", self.inputModelSelector)


    self.methodSelectorComboBox = qt.QComboBox()
    self.methodSelectorComboBox.addItem("Cleaver", METHOD_CLEAVER)
    self.methodSelectorComboBox.addItem("TetGen", METHOD_TETGEN)
    inputParametersFormLayout.addRow("Meshing method: ", self.methodSelectorComboBox)

    #
    # Outputs
    #
    outputParametersCollapsibleButton = ctk.ctkCollapsibleButton()
    outputParametersCollapsibleButton.text = "Outputs"
    self.layout.addWidget(outputParametersCollapsibleButton)
    outputParametersFormLayout = qt.QFormLayout(outputParametersCollapsibleButton)

    #
    # output volume selector
    #
    self.outputModelSelector = slicer.qMRMLNodeComboBox()
    self.outputModelSelector.nodeTypes = ["vtkMRMLModelNode"]
    self.outputModelSelector.selectNodeUponCreation = True
    self.outputModelSelector.addEnabled = True
    self.outputModelSelector.renameEnabled = True
    self.outputModelSelector.removeEnabled = True
    self.outputModelSelector.noneEnabled = False
    self.outputModelSelector.showHidden = False
    self.outputModelSelector.showChildNodeTypes = False
    self.outputModelSelector.setMRMLScene( slicer.mrmlScene )
    self.outputModelSelector.setToolTip( "Created volumetric mesh" )
    outputParametersFormLayout.addRow("Output model: ", self.outputModelSelector)

    #
    # Advanced area
    #
    self.advancedCollapsibleButton = ctk.ctkCollapsibleButton()
    self.advancedCollapsibleButton.text = "Advanced"
    self.advancedCollapsibleButton.collapsed = True
    self.layout.addWidget(self.advancedCollapsibleButton)
    advancedFormLayout = qt.QFormLayout(self.advancedCollapsibleButton)

    self.cleaverAdditionalParametersWidget = qt.QLineEdit()
    self.cleaverAdditionalParametersWidget.setToolTip('See description of parameters in module documentation ')
    advancedFormLayout.addRow("Cleaver meshing options:", self.cleaverAdditionalParametersWidget)
    self.cleaverAdditionalParametersWidget.text = "--scale 0.2 --multiplier 2 --grading 5"

    self.tetGenAdditionalParametersWidget = qt.QLineEdit()
    self.tetGenAdditionalParametersWidget.setToolTip('See description of parameters in module documentation ')
    advancedFormLayout.addRow("TetGen meshing options:", self.tetGenAdditionalParametersWidget)
    self.tetGenAdditionalParametersWidget.text = ""

    self.showDetailedLogDuringExecutionCheckBox = qt.QCheckBox(" ")
    self.showDetailedLogDuringExecutionCheckBox.checked = False
    self.showDetailedLogDuringExecutionCheckBox.setToolTip("Show detailed log during model generation.")
    advancedFormLayout.addRow("Show detailed log:", self.showDetailedLogDuringExecutionCheckBox)

    self.keepTemporaryFilesCheckBox = qt.QCheckBox(" ")
    self.keepTemporaryFilesCheckBox.checked = False
    self.keepTemporaryFilesCheckBox.setToolTip("Keep temporary files (inputs, computed outputs, logs) after the model generation is completed.")

    self.showTemporaryFilesFolderButton = qt.QPushButton("Show temp folder")
    self.showTemporaryFilesFolderButton.toolTip = "Open the folder where temporary files are stored."
    self.showTemporaryFilesFolderButton.setSizePolicy(qt.QSizePolicy.MinimumExpanding, qt.QSizePolicy.Preferred)

    hbox = qt.QHBoxLayout()
    hbox.addWidget(self.keepTemporaryFilesCheckBox)
    hbox.addWidget(self.showTemporaryFilesFolderButton)
    advancedFormLayout.addRow("Keep temporary files:", hbox)

    customCleaverPath = self.logic.getCustomCleaverPath()
    self.customCleaverPathSelector = ctk.ctkPathLineEdit()
    self.customCleaverPathSelector.setCurrentPath(customCleaverPath)
    self.customCleaverPathSelector.nameFilters = [self.logic.cleaverFilename]
    self.customCleaverPathSelector.setSizePolicy(qt.QSizePolicy.MinimumExpanding, qt.QSizePolicy.Preferred)
    self.customCleaverPathSelector.setToolTip("Set cleaver-cli executable path. "
      "If value is empty then cleaver-cli bundled with this extension will be used.")
    advancedFormLayout.addRow("Custom Cleaver executable path:", self.customCleaverPathSelector)

    customTetGenPath = self.logic.getCustomTetGenPath()
    self.customTetGenPathSelector = ctk.ctkPathLineEdit()
    self.customTetGenPathSelector.setCurrentPath(customTetGenPath)
    self.customTetGenPathSelector.nameFilters = [self.logic.tetGenFilename]
    self.customTetGenPathSelector.setSizePolicy(qt.QSizePolicy.MinimumExpanding, qt.QSizePolicy.Preferred)
    self.customTetGenPathSelector.setToolTip("Set tetgen executable path. "
      "If value is empty then tetgen bundled with this extension will be used.")
    advancedFormLayout.addRow("Custom TetGen executable path:", self.customTetGenPathSelector)

    #
    # Display
    #
    displayParametersCollapsibleButton = ctk.ctkCollapsibleButton()
    displayParametersCollapsibleButton.text = "Display"
    displayParametersCollapsibleButton.collapsed = True
    self.layout.addWidget(displayParametersCollapsibleButton)
    displayParametersFormLayout = qt.QFormLayout(displayParametersCollapsibleButton)

    self.clipNodeWidget=slicer.qMRMLClipNodeWidget()
    clipNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLClipModelsNode")
    self.clipNodeWidget.setMRMLClipNode(clipNode)
    displayParametersFormLayout.addRow(self.clipNodeWidget)

    #
    # Apply Button
    #
    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.toolTip = "Run the algorithm."
    self.applyButton.enabled = False
    self.layout.addWidget(self.applyButton)

    self.statusLabel = qt.QPlainTextEdit()
    self.statusLabel.setTextInteractionFlags(qt.Qt.TextSelectableByMouse)
    self.statusLabel.setCenterOnScroll(True)
    self.layout.addWidget(self.statusLabel)

    # connections
    self.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.showTemporaryFilesFolderButton.connect('clicked(bool)', self.onShowTemporaryFilesFolder)
    self.inputModelSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateMRMLFromGUI)
    self.outputModelSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateMRMLFromGUI)
    self.methodSelectorComboBox.connect("currentIndexChanged(int)", self.updateMRMLFromGUI)
    # Immediately update deleteTemporaryFiles in the logic to make it possible to decide to
    # keep the temporary file while the model generation is running
    self.keepTemporaryFilesCheckBox.connect("toggled(bool)", self.onKeepTemporaryFilesToggled)

    # Add vertical spacer
    self.layout.addStretch(1)

    # Refresh Apply button state
    self.updateMRMLFromGUI()

  def cleanup(self):
    pass

  def updateMRMLFromGUI(self):
    enabled = True
    if not self.inputModelSelector.currentNode():
      self.applyButton.text = "Select input segmentation"
      self.applyButton.enabled = False
    elif not self.outputModelSelector.currentNode():
      self.applyButton.text = "Select an output model node"
      self.applyButton.enabled = False
    elif self.inputModelSelector.currentNode() == self.outputModelSelector.currentNode():
      self.applyButton.text = "Choose different Output model"
      self.applyButton.enabled = False
    else:
      self.applyButton.text = "Apply"
      self.applyButton.enabled = True

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
      self.applyButton.text = "Cancelling..."
      self.applyButton.enabled = False
      return

    self.modelGenerationInProgress = True
    self.applyButton.text = "Cancel"
    self.statusLabel.plainText = ''
    slicer.app.setOverrideCursor(qt.Qt.WaitCursor)
    try:
      self.logic.setCustomCleaverPath(self.customCleaverPathSelector.currentPath)
      self.logic.setCustomTetGenPath(self.customTetGenPathSelector.currentPath)

      self.logic.deleteTemporaryFiles = not self.keepTemporaryFilesCheckBox.checked
      self.logic.logStandardOutput = self.showDetailedLogDuringExecutionCheckBox.checked

      method = self.methodSelectorComboBox.itemData(self.methodSelectorComboBox.currentIndex)
      print method
      if method == METHOD_CLEAVER:
        self.logic.createMeshFromSegmentationCleaver(self.inputModelSelector.currentNode(), self.outputModelSelector.currentNode(), self.cleaverAdditionalParametersWidget.text)
      else:
        self.logic.createMeshFromSegmentationTetGen(self.inputModelSelector.currentNode(), self.outputModelSelector.currentNode(), self.tetGenAdditionalParametersWidget.text)

    except Exception as e:
      print e
      self.addLog("Error: {0}".format(e.message))
      import traceback
      traceback.print_exc()
    finally:
      slicer.app.restoreOverrideCursor()
      self.modelGenerationInProgress = False
      self.updateMRMLFromGUI() # restores default Apply button state

  def addLog(self, text):
    """Append text to log window
    """
    self.statusLabel.appendPlainText(text)
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
      return slicer.util.toVTKString(settings.value(self.customCleaverPathSettingsKey))
    return ''

  def getCustomTetGenPath(self):
    settings = qt.QSettings()
    if settings.contains(self.customTetGenPathSettingsKey):
      return slicer.util.toVTKString(settings.value(self.customTetGenPathSettingsKey))
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
                            stdout=subprocess.PIPE, universal_newlines=True, startupinfo=info)

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

  def createMeshFromSegmentationCleaver(self, inputSegmentation, outputMeshNode, additionalParameters="--scale 0.2 --multiplier 2 --grading 5"):

    self.abortRequested = False
    tempDir = self.createTempDirectory()
    self.addLog('Mesh generation using Cleaver is started in working directory: '+tempDir)

    inputParamsCleaver = []

    # Write inputs
    qt.QDir().mkpath(tempDir)

    labelmapVolumeNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLabelMapVolumeNode')
    slicer.modules.segmentations.logic().ExportAllSegmentsToLabelmapNode(inputSegmentation, labelmapVolumeNode)
    inputLabelmapVolumeFilePath = os.path.join(tempDir, "inputLabelmap.nrrd")
    slicer.util.saveNode(labelmapVolumeNode, inputLabelmapVolumeFilePath, {"useCompression": False})
    inputParamsCleaver.extend(["--input_files", inputLabelmapVolumeFilePath])
    inputParamsCleaver.append("--segmentation")

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

    # Set up output format

    inputParamsCleaver.extend(["--output_path", tempDir+"/"])
    inputParamsCleaver.extend(["--output_format", "vtkUSG"]) # VTK unstructed grid
    inputParamsCleaver.append("--fix_tet_windup") # prevent inside-out tets
    inputParamsCleaver.append("--strip_exterior") # remove temporary elements that are added to make the volume cubic

    inputParamsCleaver.append("--verbose")

    # Quality
    inputParamsCleaver.extend(slicer.util.toVTKString(additionalParameters).split(' '))

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
        outputMeshDisplayNode.SetActiveAttributeLocation(vtk.vtkAssignAttribute.CELL_DATA);
        outputMeshDisplayNode.SetSliceIntersectionVisibility(True)
        outputMeshDisplayNode.SetSliceIntersectionOpacity(0.5)
      else:
        currentColorNode = outputMeshDisplayNode.GetColorNode()
        if currentColorNode.GetType() == currentColorNode.User and currentColorNode.IsA("vtkMRMLColorTableNode"):
          # current color table node can be overwritten
          currentColorNode.Copy(colorTableNode)
        else:
          colorTableNode = slicer.mrmlScene.AddNode(colorTableNode)
          outputMeshDisplayNode.SetAndObserveColorNodeID(colorTableNode.GetID())

    # Clean up
    if self.deleteTemporaryFiles:
      import shutil
      shutil.rmtree(tempDir)

    self.addLog("Model generation is completed")

  def createMeshFromSegmentationTetGen(self, inputSegmentation, outputMeshNode, additionalParameters=""):

    visibleSegmentIds = vtk.vtkStringArray()
    inputSegmentation.GetDisplayNode().GetVisibleSegmentIDs(visibleSegmentIds)
    if visibleSegmentIds.GetNumberOfValues() == 0:
      logging.info("createMeshFromSegmentationTetGen skipped: there are no visible segments")
      return
    inputSegmentation.CreateClosedSurfaceRepresentation()
    appender = vtk.vtkAppendPolyData()
    for i in range(visibleSegmentIds.GetNumberOfValues()):
      segmentId = visibleSegmentIds.GetValue(i)
      polydata = inputSegmentation.GetClosedSurfaceRepresentation(segmentId)
      appender.AddInputData(polydata)

    appender.Update()
    self.createMeshFromPolyDataTetGen(appender.GetOutput(), outputMeshNode, additionalParameters)

  def createMeshFromPolyDataTetGen(self, inputPolyData, outputMeshNode, additionalParameters=""):

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

    inputParamsTetGen = []
    inputParamsTetGen.append("-k"+additionalParameters)
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

    logic = TetGenLogic()
    logic.createMeshFromPolyDataTetGen(inputModelNode.GetPolyData(), outputModelNode)

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
