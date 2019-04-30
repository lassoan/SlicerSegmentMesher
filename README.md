# Segment Mesher extension

This is a 3D Slicer extension for creating volumetric meshes from segmentation using Cleaver2 or TetGen.

<a href="https://sciinstitute.github.io/cleaver.pages">Cleaver2</a> mesher is freely usable, without any restrictions.
<a href="http://www.tetgen.org">TetGen</a> mesher is only free for private, research, and educational use (see <a href="https://people.sc.fsu.edu/~jburkardt/examples/tetgen/license.txt">license</a> for details).

![Alt text](Screenshot01.jpg?raw=true "Segment Mesher module user interface")

## Installation

* Download and install a latest stable version of 3D Slicer (https://download.slicer.org).
* Start 3D Slicer application, open the Extension Manager (menu: View / Extension manager)
* Install SegmentMesher extension.

## Tutorial

* Start 3D Slicer
* Load a volume: switch to "Sample Data" module and load MRHead image
* Switch to "Segment Editor" module
* Add a new segment (it will contain the entire head)
* Fill segment by thresholding: click "Threshold" effect set 30 as lower threshold, click "Apply"
* Smooth segment: click "Smoothing" effect, set kernel size to 6mm, click "Apply"
* Add a new segment (it will contain a spherical lesion)
* Paint a sphere in the brain (simulating a lesion): click "Paint" effect, enable "Sphere brush", set "Diameter" to 8%, and click in the yellow slice view
* Switch to "Segment Mesher" module (in Segmentation category)
* Select "Create new Model" for Output model (this will contain the generated volumetric mesh)
* Click Apply button and wait a about a minute
* Inspect results: open "Display" section, enable "Yellow slice clipping", move slider at the top of yellor slice view to move the clipping plane; enable "Keep only whole cells when clipping" to see shape of mesh elements
* Create more accurate mesh: open "Advanced" section, set scale parameter to 0.5, click "Apply", and wait a couple of minutes

## Visualize and save results
* Open "Display" section to enable clipping with slices.
* Go to "Segmentations" module to hide current segmentation.
* Switch to "Models" module to adjust visualization parameters.
* To save Output model select in menu: File / Save.

![Alt text](Screenshot02.gif?raw=true "Segment meshing result (using Cleaver)")

## Mesh generation parameters

Cleaver parameters are described at https://sciinstitute.github.io/cleaver.pages/manual.html. Increase `--scale` parameter value to generate a finer resolution mesh.

TetGen parameters are described at http://wias-berlin.de/software/tetgen/1.5/doc/manual/manual005.html#sec%3Acmdline

## Acknowledgments

Cleaver is an Open Source software project that is principally funded through the SCI Institute's NIH/NIGMS CIBC Center. Please use the following acknowledgment and send references to any publications, presentations, or successful funding applications that make use of NIH/NIGMS CIBC software or data sets to <a href="http://www.sci.utah.edu/software/cleaver.html">SCI</a>: "This project was supported by the National Institute of General Medical Sciences of the National Institutes of Health under grant number P41 GM103545-18."


TetGen citation: Si, Hang (2015). "TetGen, a Delaunay-based Tetrahedral Mesh Generator". ACM Transactions on Mathematical Software. 41 (2): 11:1-11:36. doi:10.1145/2629697
