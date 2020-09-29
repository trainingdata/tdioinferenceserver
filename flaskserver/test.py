import pytest
from api.utils import open3dSlicer

pythonScriptContent1 = "import slicer, vtk\nimport SimpleITK as sitk\nimport sitkUtils\ndef loadMasterAndSegmentationVolume(masterVolumeNiiPath, segmentationVolumeNiiPath):\n    masterVolumeNode = slicer.util.loadVolume(masterVolumeNiiPath)\n    labelmapVolumeNode = slicer.util.loadLabelVolume(segmentationVolumeNiiPath)\n#    labelImage = sitk.ReadImage(segmentationVolumeNiiPath)\n#    labelmapVolumeNode = sitkUtils.PushVolumeToSlicer(labelImage, None, className='vtkMRMLLabelMapVolumeNode')\n    segmentIDArray = vtk.vtkStringArray()\n#    segmentIDArray.SetNumberOfValues(1)\n    segmentIDArray.SetValue(0, 'test')\n    slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(labelmapVolumeNode, masterVolumeNode, segmentIDArray)\n\nloadMasterAndSegmentationVolume({}, {})"

def test_open3dSlicer():
   pythonScript = pythonScriptContent1.format("\'/home/gaurav/workspace/trainingdataIO/trainingdataIO/cvat/dockerdicomviewer/radiologyannotation/flaskmicroservices/a95a90f9-8de9-4f47-948d-d14bcd49be0b.nii.gz\'", "\'/home/gaurav/workspace/trainingdataIO/trainingdataIO/cvat/dockerdicomviewer/radiologyannotation/flaskmicroservices/a95a90f9-8de9-4f47-948d-d14bcd49be0b-result.nii.gz\'")
   open3dSlicer(pythonScript)

'''   
import slicer, vtk
import SimpleITK as sitk
import sitkUtils
def loadMasterAndSegmentationVolume(masterVolumeNiiPath, segmentationVolumeNiiPath):
   masterVolumeNode = slicer.util.loadVolume(masterVolumeNiiPath)
   labelmapVolumeNode = slicer.util.loadLabelVolume(segmentationVolumeNiiPath)
   #    labelImage = sitk.ReadImage(segmentationVolumeNiiPath)
   #    labelmapVolumeNode = sitkUtils.PushVolumeToSlicer(labelImage, None, className='vtkMRMLLabelMapVolumeNode')
   segmentIDArray = vtk.vtkStringArray()
   #    segmentIDArray.SetNumberOfValues(1)
   segmentIDArray.SetValue(0, 'test')
   slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(labelmapVolumeNode, masterVolumeNode, segmentIDArray)

   loadMasterAndSegmentationVolume({}, {})
'''
