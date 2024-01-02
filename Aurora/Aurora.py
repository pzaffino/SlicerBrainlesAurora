import logging
import os
from typing import Annotated, Optional

import vtk, ctk, qt

import slicer
from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from slicer.parameterNodeWrapper import (
    parameterNodeWrapper,
    WithinRange,
)

import SimpleITK as sitk
import sitkUtils

import tempfile

#from slicer import vtkMRMLScalarVolumeNode


#
# Aurora
#


class Aurora(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = _("Aurora")  # TODO: make this more human readable by adding spaces
        # TODO: set categories (folders where the module shows up in the module selector)
        self.parent.categories = [translate("qSlicerAbstractCoreModule", "Examples")]
        self.parent.dependencies = []  # TODO: add here list of module names that this module requires
        self.parent.contributors = ["Paolo Zaffino (Magna Graecia University of Catanzaro, Italy)", "Maria Francesca Spadea (Karlsruhe Institute of Technology, Germany)"]  # TODO: replace with "Firstname Lastname (Organization)"
        # TODO: update with short description of the module and a link to online module documentation
        # _() function marks text as translatable to other languages
        self.parent.helpText = _("""
This is an example of scripted loadable module bundled in an extension.
See more information in <a href="https://github.com/organization/projectname#Aurora">module documentation</a>.
""")
        # TODO: replace with organization, grant and thanks
        self.parent.acknowledgementText = _("""
This module is based on the Vincenzo Vellone's master thesis. Brainles Aurora was developed by Dr. Florian Kofler and his team.
""")


#
# Register sample data sets in Sample Data module
#


#
# AuroraWidget
#


class AuroraWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """
    def setup(self):
      ScriptedLoadableModuleWidget.setup(self)

      # Instantiate and connect widgets ...

      #
      # Parameters Area
      #
      parametersCollapsibleButton = ctk.ctkCollapsibleButton()
      parametersCollapsibleButton.text = "Parameters"
      self.layout.addWidget(parametersCollapsibleButton)

      # Layout within the dummy collapsible button
      parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

      #
      # T1 volume selector
      #
      self.T1cSelector = slicer.qMRMLNodeComboBox()
      self.T1cSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
      self.T1cSelector.selectNodeUponCreation = True
      self.T1cSelector.addEnabled = False
      self.T1cSelector.removeEnabled = False
      self.T1cSelector.noneEnabled = False
      self.T1cSelector.showHidden = False
      self.T1cSelector.showChildNodeTypes = False
      self.T1cSelector.setMRMLScene(slicer.mrmlScene)
      self.T1cSelector.setToolTip( "Select the T1 weighted contrast" )
      parametersFormLayout.addRow("T1 weighted contrast volume: ", self.T1cSelector)

      #
      # output volume selector
      #

      self.segmentationOutputSelector = slicer.qMRMLNodeComboBox()
      self.segmentationOutputSelector.nodeTypes = ["vtkMRMLSegmentationNode"]
      self.segmentationOutputSelector.selectNodeUponCreation = True
      self.segmentationOutputSelector.addEnabled = True
      self.segmentationOutputSelector.removeEnabled = True
      self.segmentationOutputSelector.noneEnabled = True
      self.segmentationOutputSelector.showHidden = False
      self.segmentationOutputSelector.showChildNodeTypes = False
      self.segmentationOutputSelector.setMRMLScene(slicer.mrmlScene)
      self.segmentationOutputSelector.baseName = "Brain segmentation"
      self.segmentationOutputSelector.setToolTip("Select or create a segmentation for brain tissue classification")
      parametersFormLayout.addRow("Output segmentation: ", self.segmentationOutputSelector)

      #
      # Apply Button
      #
      self.applyButton = qt.QPushButton("Apply (it can take some minutes)")
      self.applyButton.toolTip = "Run the algorithm."
      self.applyButton.enabled = False
      parametersFormLayout.addRow(self.applyButton)

      # connections
      self.applyButton.connect('clicked(bool)', self.onApplyButton)
      self.T1cSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
      self.segmentationOutputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)

      # Add vertical spacer
      self.layout.addStretch(1)

      # Refresh Apply button state
      self.onSelect()

      # Create logic object
      self.logic = AuroraLogic()

    def onSelect(self):
      self.applyButton.enabled = self.T1cSelector.currentNode() and self.segmentationOutputSelector.currentNode()


    def onApplyButton(self):
      self.logic.run(self.T1cSelector.currentNode(), self.segmentationOutputSelector.currentNode())


#
# AuroraLogic
#


class AuroraLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self) -> None:
        """Called when the logic class is instantiated. Can be used for initializing member variables."""
        ScriptedLoadableModuleLogic.__init__(self)

    def AuroraErrorBox(self):
        errorMBox = qt.QMessageBox()
        errorMBox.setIcon(qt.QMessageBox().Critical)
        errorMBox.setWindowTitle("Error")
        errorMBox.setText("Error in brain segmentation")
        errorMBox.exec()

    def run(self, T1cNode, segmentationOutputNode):

        # Import the required libraries
        try:
          from brainles_aurora.lib import single_inference
        except ModuleNotFoundError:
          slicer.util.pip_install("brainles-aurora")
          from brainles_aurora.lib import single_inference

        T1c_sitk = sitk.Cast(sitkUtils.PullVolumeFromSlicer(T1cNode.GetName()), sitk.sitkFloat32)

        with tempfile.NamedTemporaryFile(suffix='.nii') as T1c_tempfile:
            with tempfile.NamedTemporaryFile(suffix='.nii') as outputSegmentation_tempfile:
                sitk.WriteImage(T1c_sitk, T1c_tempfile.name)

                # Run inference
                print('Running inference')
                single_inference(t1c_file=T1c_tempfile.name, segmentation_file=outputSegmentation_tempfile.name, tta=False, verbosity=True)

                outputSegmentation_sitk=sitk.ReadImage(outputSegmentation_tempfile.name)

        labelmap = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
        labelmap = sitkUtils.PushVolumeToSlicer(outputSegmentation_sitk, labelmap)

        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(labelmap, segmentationOutputNode)
        segmentationOutputNode.CreateClosedSurfaceRepresentation()
        slicer.mrmlScene.RemoveNode(labelmap)


#
# AuroraTest
#


class AuroraTest(ScriptedLoadableModuleTest):
    """
    This is the test case for your scripted module.
    Uses ScriptedLoadableModuleTest base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setUp(self):
        """Do whatever is needed to reset the state - typically a scene clear will be enough."""
        slicer.mrmlScene.Clear()

    def runTest(self):
        """Run as few or as many tests as needed here."""
        self.setUp()
        self.test_Aurora1()

    def test_Aurora1(self):
        """Ideally you should have several levels of tests.  At the lowest level
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

