import os
import slicer

def loadMasterAndSegmentationVolume(masterVolumeNiiPath, segmentationVolumeNiiPath):
    [success, masterVolumeNode] = slicer.util.loadVolume(masterVolumeNiiPath, returnNode=True)

    if not success:
        print('Failed to load volume:', masterVolumeNiiPath)
    [success, segmentationVolumeNode = slicer.util.loadVolume(segmentationVolumeNiiPath, returnNode=True)
