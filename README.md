# Segment Mesher extension

This is an extenion for 3D Slicer for creating volumetric meshes from segmentation using Cleaver2 or TetGen.

<a href="https://sciinstitute.github.io/cleaver.pages">Cleaver2</a> mesher is freely usable, without any restrictions.
<a href="http://www.tetgen.org">TetGen</a> mesher is only free for private, research, and educational use (see <a href="https://people.sc.fsu.edu/~jburkardt/examples/tetgen/license.txt">license</a> for details).

![Alt text](Screenshot01.jpg?raw=true "Segment Mesher module user interface")

## Installation

* Download and install a recent nightly version of 3D Slicer (https://download.slicer.org).
* Start 3D Slicer application, open the Extension Manager (menu: View / Extension manager)
* Install SegmentMesher extension.

## Tutorial

* Start 3D Slicer
* Load a volume (for example: switch to SampleData module and load MRBrainTumor1 imaage)
* Switch to Mesh Segmenter module (in Segmentation category)
* Select "Create new Model" for Output model (this will contain the generated volumetric mesh)
* Click Apply button and wait a about a minute

## Visualize and save results
* Open "Display" section to enable clipping with slices.
* Go to "Segmentations" module to hide current segmentation.
* Switch to "Models" module to adjust visualization parameters.
* To save Output model select in menu: File / Save.

![Alt text](Screenshot02.gif?raw=true "Segment meshing result (using Cleaver)")

## Mesh generation parameters

Cleaver parameters are described at https://sciinstitute.github.io/cleaver.pages/manual.html

TetGen parameters are described at http://wias-berlin.de/software/tetgen/1.5/doc/manual/manual005.html#sec%3Acmdline

## Acknowledgments

Cleaver is an Open Source software project that is principally funded through the SCI Institute's NIH/NIGMS CIBC Center. Please use the following acknowledgment and send references to any publications, presentations, or successful funding applications that make use of NIH/NIGMS CIBC software or data sets to <a href="http://www.sci.utah.edu/software/cleaver.html">SCI</a>: "This project was supported by the National Institute of General Medical Sciences of the National Institutes of Health under grant number P41 GM103545-18."


TetGen citation: Si, Hang (2015). "TetGen, a Delaunay-based Tetrahedral Mesh Generator". ACM Transactions on Mathematical Software. 41 (2): 11:1-11:36. doi:10.1145/2629697
