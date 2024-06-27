from __future__ import print_function
import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
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

class SegmentMesherWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent=None):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)  # needed for parameter node observation
    self.logic = None
    self._parameterNode = None
    self._updatingGUIFromParameterNode = False

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
    self.ui.inputSegmentationSelector.setMRMLScene( slicer.mrmlScene )
    self.ui.inputModelSelector.setMRMLScene( slicer.mrmlScene )
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

    # These connections ensure that we update parameter node when scene is closed
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

    # connections
    self.ui.selectAllSegmentsButton.connect('clicked(bool)', self.onSelectAllSegmentsButton)
    self.ui.applyButton.connect('clicked(bool)', self.onApplyButton)
    self.ui.showTemporaryFilesFolderButton.connect('clicked(bool)', self.onShowTemporaryFilesFolder)
    self.ui.inputSegmentationSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateMRMLFromGUI)
    self.ui.inputModelSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateMRMLFromGUI)
    self.ui.outputModelSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateMRMLFromGUI)
    self.ui.methodSelectorComboBox.connect("currentIndexChanged(int)", self.updateMRMLFromGUI)
    # Immediately update deleteTemporaryFiles in the logic to make it possible to decide to
    # keep the temporary file while the model generation is running
    self.ui.keepTemporaryFilesCheckBox.connect("toggled(bool)", self.onKeepTemporaryFilesToggled)
    self.ui.tetgenUseSurface.connect("toggled(bool)", self.updateMRMLFromGUI)

    #Parameter node connections
    self.ui.inputSegmentationSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.inputModelSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.outputModelSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.methodSelectorComboBox.connect("currentIndexChanged(int)", self.updateParameterNodeFromGUI)


    self.ui.showDetailedLogDuringExecutionCheckBox.connect("toggled(bool)", self.updateParameterNodeFromGUI)
    self.ui.keepTemporaryFilesCheckBox.connect("toggled(bool)", self.updateParameterNodeFromGUI)

    self.ui.cleaverFeatureScalingParameterWidget.connect("valueChanged(double)", self.updateParameterNodeFromGUI)
    self.ui.cleaverSamplingParameterWidget.connect("valueChanged(double)", self.updateParameterNodeFromGUI)
    self.ui.cleaverRateParameterWidget.connect("valueChanged(double)", self.updateParameterNodeFromGUI)
    self.ui.cleaverAdditionalParametersWidget.connect("textChanged(const QString&)", self.updateParameterNodeFromGUI)
    self.ui.cleaverRemoveBackgroundMeshCheckBox.connect("toggled(bool)", self.updateParameterNodeFromGUI)
    self.ui.cleaverPaddingPercentSpinBox.connect("valueChanged(int)", self.updateParameterNodeFromGUI)
    self.ui.customCleaverPathSelector.connect("currentPathChanged(const QString&)", self.updateParameterNodeFromGUI)

    self.ui.tetgenUseSurface.connect("toggled(bool)", self.updateParameterNodeFromGUI)
    self.ui.tetgenRatioParameterWidget.connect("valueChanged(double)", self.updateParameterNodeFromGUI)
    self.ui.tetgenAngleParameterWidget.connect("valueChanged(double)", self.updateParameterNodeFromGUI)
    self.ui.tetgenVolumeParameterWidget.connect("valueChanged(double)", self.updateParameterNodeFromGUI)
    self.ui.tetGenAdditionalParametersWidget.connect("textChanged(const QString&)", self.updateParameterNodeFromGUI)
    self.ui.customTetGenPathSelector.connect("currentPathChanged(const QString&)", self.updateParameterNodeFromGUI)

    # Add vertical spacer
    self.layout.addStretch(1)

    # Make sure parameter node is initialized (needed for module reload)
    self.initializeParameterNode()
    self.ui.parameterNodeSelector.setCurrentNode(self._parameterNode)
    self.ui.parameterNodeSelector.connect("currentNodeChanged(vtkMRMLNode*)",  self.setParameterNode)

    # Refresh Apply button state
    self.updateMRMLFromGUI()

  def enter(self):
    """
    Called each time the user opens this module.
    """
    # Make sure parameter node exists and observed
    self.initializeParameterNode()
    self.updateMRMLFromGUI()

  def cleanup(self):
    """
    Called when the application closes and the module widget is destroyed.
    """
    self.removeObservers()

  def exit(self):
    """
    Called each time the user opens a different module.
    """
    # Do not react to parameter node changes (GUI wlil be updated when the user enters into the module)
    self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

  def onSceneStartClose(self, caller, event):
    """
    Called just before the scene is closed.
    """
    # Parameter node will be reset, do not use it anymore
    self.setParameterNode(None)

  def onSceneEndClose(self, caller, event):
    """
    Called just after the scene is closed.
    """
    # If this module is shown while the scene is closed then recreate a new parameter node immediately
    if self.parent.isEntered:
      self.initializeParameterNode()


  def initializeParameterNode(self):
    """
    Ensure parameter node exists and observed.
    """
    # Parameter node stores all user choices in parameter values, node selections, etc.
    # so that when the scene is saved and reloaded, these settings are restored.

    self.setParameterNode(self.logic.getParameterNode())

    # Select default input nodes if nothing is selected yet to save a few clicks for the user
    if not self._parameterNode.GetNodeReference("InputSegmentation"):
      firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLSegmentationNode")
      if firstVolumeNode:
        self._parameterNode.SetNodeReferenceID("InputSegmentation", firstVolumeNode.GetID())

    # Select default input nodes if nothing is selected yet to save a few clicks for the user
    if not self._parameterNode.GetNodeReference("InputSurface"):
      firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLModelNode")
      if firstVolumeNode:
        self._parameterNode.SetNodeReferenceID("InputSurface", firstVolumeNode.GetID())

  def setParameterNode(self, inputParameterNode):
    """
    Set and observe parameter node.
    Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
    """

    if inputParameterNode:
      self.logic.setDefaultParameters(inputParameterNode)

    # Unobserve previously selected parameter node and add an observer to the newly selected.
    # Changes of parameter node are observed so that whenever parameters are changed by a script or any other module
    # those are reflected immediately in the GUI.
    if self._parameterNode is not None:
      self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
    self._parameterNode = inputParameterNode
    if self._parameterNode is not None:
      self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

    # Initial GUI update
    self.updateGUIFromParameterNode()

  def updateGUIFromParameterNode(self, caller=None, event=None):
    """
    This method is called whenever parameter node is changed.
    The module GUI is updated to show the current state of the parameter node.
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    # Make sure GUI changes do not call updateParameterNodeFromGUI (it could cause infinite loop)
    self._updatingGUIFromParameterNode = True

    # Update node selectors and sliders
    self.ui.inputSegmentationSelector.setCurrentNode(self._parameterNode.GetNodeReference("InputSegmentation"))
    self.ui.inputModelSelector.setCurrentNode(self._parameterNode.GetNodeReference("InputSurface"))
    self.ui.outputModelSelector.setCurrentNode(self._parameterNode.GetNodeReference("OutputModel"))
    self.ui.methodSelectorComboBox.setCurrentText(self._parameterNode.GetParameter("Method"))

    self.ui.showDetailedLogDuringExecutionCheckBox.checked = (self._parameterNode.GetParameter("showDetailedLogDuringExecution") == "true")
    self.ui.keepTemporaryFilesCheckBox.checked = (self._parameterNode.GetParameter("keepTemporaryFiles") == "true")

    self.ui.cleaverFeatureScalingParameterWidget.value = float(self._parameterNode.GetParameter("cleaverFeatureScalingParameter"))
    self.ui.cleaverSamplingParameterWidget.value = float(self._parameterNode.GetParameter("cleaverSamplingParameter"))
    self.ui.cleaverRateParameterWidget.value = float(self._parameterNode.GetParameter("cleaverRateParameter"))
    self.ui.cleaverAdditionalParametersWidget.text = self._parameterNode.GetParameter("cleaverAdditionalParameters")
    self.ui.cleaverRemoveBackgroundMeshCheckBox.checked = (self._parameterNode.GetParameter("cleaverRemoveBackgroundMesh") == "true")
    self.ui.cleaverPaddingPercentSpinBox.value = int(self._parameterNode.GetParameter("cleaverPaddingPercent"))
    self.ui.customCleaverPathSelector.setCurrentPath(self._parameterNode.GetParameter("customCleaverPath"))

    self.ui.tetgenUseSurface.checked = (self._parameterNode.GetParameter("tetgenUseSurface") == "true")
    self.ui.tetgenRatioParameterWidget.value = float(self._parameterNode.GetParameter("tetgenRatioParameter"))
    self.ui.tetgenAngleParameterWidget.value = float(self._parameterNode.GetParameter("tetgenAngleParameter"))
    self.ui.tetgenVolumeParameterWidget.value = float(self._parameterNode.GetParameter("tetgenVolumeParameter"))
    self.ui.tetGenAdditionalParametersWidget.text = self._parameterNode.GetParameter("tetGenAdditionalParameters")
    self.ui.customTetGenPathSelector.setCurrentPath(self._parameterNode.GetParameter("customTetGenPath"))


    # Update buttons states and tooltips
    self.updateMRMLFromGUI()

    # All the GUI updates are done
    self._updatingGUIFromParameterNode = False

  def updateParameterNodeFromGUI(self, caller=None, event=None):
    """
    This method is called when the user makes any change in the GUI.
    The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    wasModified = self._parameterNode.StartModify()  # Modify all properties in a single batch

    #Inputs/Outputs
    self._parameterNode.SetNodeReferenceID("InputSegmentation", self.ui.inputSegmentationSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID("InputSurface", self.ui.inputModelSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID("OutputModel", self.ui.outputModelSelector.currentNodeID)
    self._parameterNode.SetParameter("Method", self.ui.methodSelectorComboBox.currentText)

    #General parameters
    self._parameterNode.SetParameter("showDetailedLogDuringExecution", "true" if self.ui.showDetailedLogDuringExecutionCheckBox.checked else "false")
    self._parameterNode.SetParameter("keepTemporaryFiles", "true" if self.ui.keepTemporaryFilesCheckBox.checked else "false")

    #Cleaver parameters
    self._parameterNode.SetParameter("cleaverFeatureScalingParameter", str(self.ui.cleaverFeatureScalingParameterWidget.value))
    self._parameterNode.SetParameter("cleaverSamplingParameter", str(self.ui.cleaverSamplingParameterWidget.value))
    self._parameterNode.SetParameter("cleaverRateParameter", str(self.ui.cleaverRateParameterWidget.value))
    self._parameterNode.SetParameter("cleaverAdditionalParameters", self.ui.cleaverAdditionalParametersWidget.text)
    self._parameterNode.SetParameter("cleaverRemoveBackgroundMesh", "true" if self.ui.cleaverRemoveBackgroundMeshCheckBox.checked else "false")
    self._parameterNode.SetParameter("cleaverPaddingPercent", str(self.ui.cleaverPaddingPercentSpinBox.value))
    self._parameterNode.SetParameter("customCleaverPath", self.ui.customCleaverPathSelector.currentPath)

    #TetGen parameters
    self._parameterNode.SetParameter("tetgenUseSurface", "true" if self.ui.tetgenUseSurface.checked else "false")
    self._parameterNode.SetParameter("tetgenRatioParameter", str(self.ui.tetgenRatioParameterWidget.value))
    self._parameterNode.SetParameter("tetgenAngleParameter", str(self.ui.tetgenAngleParameterWidget.value))
    self._parameterNode.SetParameter("tetgenVolumeParameter", str(self.ui.tetgenVolumeParameterWidget.value))
    self._parameterNode.SetParameter("tetGenAdditionalParameters", self.ui.tetGenAdditionalParametersWidget.text)
    self._parameterNode.SetParameter("customTetGenPath", self.ui.customTetGenPathSelector.currentPath)

    self._parameterNode.EndModify(wasModified)

  def updateMRMLFromGUI(self):

    method = self.ui.methodSelectorComboBox.itemData(self.ui.methodSelectorComboBox.currentIndex)

    #Enable correct input selections
    inputIsModel = (self.ui.tetgenUseSurface.isChecked() and method == METHOD_TETGEN)
    self.ui.inputSegmentationLabel.visible = not inputIsModel
    self.ui.inputSegmentationSelector.visible = not inputIsModel
    self.ui.segmentSelectorLabel.visible = not inputIsModel
    self.ui.segmentSelectorCombBox.visible = not inputIsModel
    self.ui.inputModelLabel.visible = inputIsModel
    self.ui.inputModelSelector.visible = inputIsModel
    segmentationSelected = self.ui.inputSegmentationSelector.currentNode() is not None
    self.ui.segmentSelectorCombBox.enabled = segmentationSelected
    self.ui.selectAllSegmentsButton.enabled = segmentationSelected

    #populate segments
    inputSeg = self.ui.inputSegmentationSelector.currentNode()
    oldIndex = self.ui.segmentSelectorCombBox.checkedIndexes()
    oldCount = self.ui.segmentSelectorCombBox.count
    self.ui.segmentSelectorCombBox.clear()
    if inputSeg is not None:
      segmentIDs = vtk.vtkStringArray()
      inputSeg.GetSegmentation().GetSegmentIDs(segmentIDs)
      for index in range(0, segmentIDs.GetNumberOfValues()):
        segmentId = segmentIDs.GetValue(index)
        self.ui.segmentSelectorCombBox.addItem(inputSeg.GetSegmentation().GetSegment(segmentId).GetName(), segmentId)

    #Restore index - often we will be reloading the data from the same segmentation, so re-select items number of items is the same
    if oldCount == self.ui.segmentSelectorCombBox.count:
      for index in oldIndex:
        self.ui.segmentSelectorCombBox.setCheckState(index, qt.Qt.Checked)

    self.ui.CleaverParametersGroupBox.visible = (method == METHOD_CLEAVER)
    self.ui.TetGenParametersGroupBox.visible = (method == METHOD_TETGEN)

    if method == METHOD_TETGEN and self.ui.tetgenUseSurface.isChecked():
      if not self.ui.inputModelSelector.currentNode():
        self.ui.applyButton.text = "Select input surface"
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
    else:
      if not self.ui.inputSegmentationSelector.currentNode():
        self.ui.applyButton.text = "Select input segmentation"
        self.ui.applyButton.enabled = False
      elif not self.ui.outputModelSelector.currentNode():
        self.ui.applyButton.text = "Select an output model node"
        self.ui.applyButton.enabled = False
      elif self.ui.inputSegmentationSelector.currentNode() == self.ui.outputModelSelector.currentNode():
        self.ui.applyButton.text = "Choose different Output model"
        self.ui.applyButton.enabled = False
      else:
        self.ui.applyButton.text = "Apply"
        self.ui.applyButton.enabled = True

    self.updateParameterNodeFromGUI()


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
        segments.append(self.ui.segmentSelectorCombBox.itemData(index.row()))

      print(method)
      if method == METHOD_CLEAVER:
        self.logic.createMeshFromSegmentationCleaver(self.ui.inputSegmentationSelector.currentNode(),
          self.ui.outputModelSelector.currentNode(), segments, self.ui.cleaverAdditionalParametersWidget.text,
          self.ui.cleaverRemoveBackgroundMeshCheckBox.isChecked(),
          self.ui.cleaverPaddingPercentSpinBox.value * 0.01, self.ui.cleaverFeatureScalingParameterWidget.value, self.ui.cleaverSamplingParameterWidget.value, self.ui.cleaverRateParameterWidget.value)
      else:
        if self.ui.tetgenUseSurface.isChecked():
          if self.ui.inputModelSelector.currentNode().GetUnstructuredGrid() is not None:
            self.addLog("Error: Mesh must be a surface, not volumetric")
            return
          self.logic.createMeshFromPolyDataTetGen(self.ui.inputModelSelector.currentNode().GetPolyData(),
            self.ui.outputModelSelector.currentNode(), self.ui.tetGenAdditionalParametersWidget.text,
            self.ui.tetgenRatioParameterWidget.value, self.ui.tetgenAngleParameterWidget.value, self.ui.tetgenVolumeParameterWidget.value)
        else:
          self.logic.createMeshFromSegmentationTetGen(self.ui.inputSegmentationSelector.currentNode(),
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

  def onSelectAllSegmentsButton(self):
      newState = qt.Qt.Unchecked if self.ui.segmentSelectorCombBox.allChecked() else qt.Qt.Checked
      model = self.ui.segmentSelectorCombBox.model()
      for i in range(self.ui.segmentSelectorCombBox.count):
        self.ui.segmentSelectorCombBox.setCheckState(model.index(i, 0), newState)

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

  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    self.setParameterIfNotDefined(parameterNode, "showDetailedLogDuringExecution", "false")
    self.setParameterIfNotDefined(parameterNode, "keepTemporaryFiles", "false")

    self.setParameterIfNotDefined(parameterNode, "cleaverFeatureScalingParameter", "2.0")
    self.setParameterIfNotDefined(parameterNode, "cleaverSamplingParameter", "0.2")
    self.setParameterIfNotDefined(parameterNode, "cleaverRateParameter", "0.2")
    self.setParameterIfNotDefined(parameterNode, "cleaverAdditionalParameters", "")
    self.setParameterIfNotDefined(parameterNode, "cleaverRemoveBackgroundMesh", "true")
    self.setParameterIfNotDefined(parameterNode, "cleaverPaddingPercent", "10")
    self.setParameterIfNotDefined(parameterNode, "customCleaverPath", "")

    self.setParameterIfNotDefined(parameterNode, "tetgenUseSurface", "false")
    self.setParameterIfNotDefined(parameterNode, "tetgenRatioParameter", "5")
    self.setParameterIfNotDefined(parameterNode, "tetgenAngleParameter", "5")
    self.setParameterIfNotDefined(parameterNode, "tetgenVolumeParameter", "5")
    self.setParameterIfNotDefined(parameterNode, "tetGenAdditionalParameters", "")
    self.setParameterIfNotDefined(parameterNode, "customTetGenPath", "")


  def setParameterIfNotDefined(self, parameterNode, key, value):
    if not parameterNode.GetParameter(key):
      parameterNode.SetParameter(key, value)

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

  def createMeshFromSegmentationCleaver(self, inputSegmentation, outputMeshNode, segments = [], additionalParameters = None, removeBackgroundMesh = False,
    paddingRatio = 0.10, featureScale = 2, samplingRate=0.2, rateOfChange=0.2):

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
      self.addLog("No input segments are selected, therefore no output is generated.")
      return

    slicer.modules.segmentations.logic().ExportSegmentsToLabelmapNode(inputSegmentation, segmentIdList, labelmapVolumeNode, labelmapVolumeNode)


    inputLabelmapVolumeFilePath = os.path.join(tempDir, "inputLabelmap.nrrd")
    slicer.util.saveNode(labelmapVolumeNode, inputLabelmapVolumeFilePath, {"useCompression": False})
    inputParamsCleaver.extend(["--input_files", inputLabelmapVolumeFilePath])

    # Keep IJK to RAS matrix, we'll need it later
    unscaledIjkToRasMatrix = vtk.vtkMatrix4x4()
    labelmapVolumeNode.GetIJKToRASDirectionMatrix(unscaledIjkToRasMatrix)  # axis directions, without scaling by spacing
    ijkToRasMatrix = vtk.vtkMatrix4x4()
    labelmapVolumeNode.GetIJKToRASMatrix(ijkToRasMatrix)
    origin = ijkToRasMatrix.MultiplyPoint([-0.5, -0.5, -0.5, 1.0])  # Cleaver uses the voxel corner as its origin, therefore we need a half-voxel offset
    for i in range(3):
      unscaledIjkToRasMatrix.SetElement(i,3, origin[i])

    # Keep color node, we'll need it later
    colorTableNode = labelmapVolumeNode.GetDisplayNode().GetColorNode()
    # Background color is transparent by default which is not ideal for 3D display
    colorTableNode.SetColor(0,0.6,0.6,0.6,1.0)

    slicer.mrmlScene.RemoveNode(labelmapVolumeNode)
    slicer.mrmlScene.RemoveNode(colorTableNode)

    #User set parameters
    inputParamsCleaver.extend(["--feature_scaling", "{:.2f}".format(featureScale)])
    inputParamsCleaver.extend(["--sampling_rate", "{:.2f}".format(samplingRate)])
    inputParamsCleaver.extend(["--lipschitz", "{:.2f}".format(rateOfChange)])

    # Set up output format

    inputParamsCleaver.extend(["--output_path", tempDir+"/"])
    inputParamsCleaver.extend(["--output_format", "vtkUSG"]) # VTK unstructed grid
    inputParamsCleaver.append("--fix_tet_windup") # prevent inside-out tets
    inputParamsCleaver.append("--strip_exterior") # remove temporary elements that are added to make the volume cubic

    inputParamsCleaver.append("--verbose")

    # Quality
    if additionalParameters:
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
        backgroundMeshRemover.SetLowerThreshold(1)
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
    parameters = 'q'+"{:.2f}".format(ratio)+'/'+"{:.2f}".format(angle)+'a'+"{:.2f}".format(volume)

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
