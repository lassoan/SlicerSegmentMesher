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

Cleaver parameters are described at https://sciinstitute.github.io/cleaver.pages/manual.html. To make the output mesh elements smaller: decrease value of `--feature_scaling`. To make the output mesh preserve small details (at the cost of more computation time and memory usage): increase `--sampling-rate` (up to 1.0).

```
  Input data:
  -i [ --input_files ] arg           material field paths or segmentation path
                                     This argument is set automatically by SlicerSegmentMesher module.
  -B [ --blend_sigma ] arg           blending function sigma for input(s) to
                                     remove alias artifacts.
                                     Too low value will not remove staircase artifacts.
                                     Too high value may shrink structures and remove relevant details.
                                     Default: 1.0.

  Output data:
  -f [ --output_format ] arg         output mesh format (tetgen [default],
                                     scirun, matlab, vtkUSG, vtkPoly, ply
                                     [surface mesh only])
                                     This argument is set automatically by SlicerSegmentMesher module to vtkUSG.
  -n [ --output_name ] arg           output mesh name (default 'output')
                                     This argument is set automatically by SlicerSegmentMesher module.
  -o [ --output_path ] arg           output path prefix
                                     This argument is set automatically by SlicerSegmentMesher module.

  Meshing mode (element size control):
  -m [ --element_sizing_method ] arg background mesh mode (adaptive [default],
                                     constant)

  For constant mode:
  -a [ --alpha ] arg                 initial alpha value, default: 0.4
  -s [ --alpha_short ] arg           alpha short value for constant element
                                     sizing method, default: 0.203
  -l [ --alpha_long ] arg            alpha long value for constant element
                                     sizing method, default: 0.357

  For adaptive mode:
  -F [ --feature_scaling ] arg       feature size scaling (higher values make a
                                     coarser mesh), default: 1.0.
                                     Meaningful range is about 0.2 to 5.0.
                                     Lower value makes the output mesh finer,
                                     higher value makes the output mesh coarser and meshing faster.
  -L [ --lipschitz ] arg             maximum rate of change of element size (1
                                     is uniform), default: 0.2
                                     It specifies how quickly the sizing field may grow away from size-limiting
                                     features (like corners or curved interfaces).
  -R [ --sampling_rate ] arg         volume sampling rate (lower values make a
                                     coarser mesh), default: 1.0 (full sampling)
                                     Meaningful range is 0.1 to 1.0.
                                     Lower value makes meshing faster, higher value
                                     preserves fine details.

  Advanced:
  -b [ --background_mesh ] arg       input background mesh
  -I [ --indicator_functions ]       the input files are indicator functions (boundary is defined as isosurface
                                     where image value = 0)
  -z [ --sizing_field ] arg          sizing field path (use precomputed sizing field for adaptive mode)
  -w [ --write_background_mesh ]     write background mesh
  --simple                           use simple interface approximation
  -j [ --fix_tet_windup ]            ensure positive Jacobians with proper vertex wind-up
                                     (prevents inside-out tetrahedra in the output mesh)
                                     This flag is specified by SlicerSegmentMesher module, no need to specify it as additional option.
  -e [ --strip_exterior ]            strip exterior tetrahedra (remove temporary elements that are added to make the volume cubic)
                                     This flag is specified by SlicerSegmentMesher module, no need to specify it as additional option.

  Other:
    -h [ --help ]                      display help message
    -r [ --record ] arg                record operations on tets from input file
    -t [ --strict ]                    warnings become errors
    -v [ --verbose ]                   enable verbose output
                                       This flag is specified by SlicerSegmentMesher module (based on Verbose option).
    -V [ --version ]                   display version information
```

TetGen parameters are described at http://wias-berlin.de/software/tetgen/1.5/doc/manual/manual005.html#sec%3Acmdline

## Developers

### Split mesh to submeshes

```python
meshNode = getNode('Model')
mesh = meshNode.GetMesh()
cellData = mesh.GetCellData()
labelsRange = cellData.GetArray("labels").GetRange()
for labelValue in range(int(labelsRange[0]), int(labelsRange[1]+1)):
    threshold = vtk.vtkThreshold()
    threshold.SetInputData(mesh)
    threshold.SetInputArrayToProcess(0, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_CELLS, "labels")
    threshold.ThresholdBetween(labelValue, labelValue)
    threshold.Update()
    if threshold.GetOutput().GetNumberOfPoints() > 0:
        modelNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", "{0}_{1}".format(meshNode.GetName(), labelValue))
        modelNode.SetAndObserveMesh(threshold.GetOutput())
        modelNode.CreateDefaultDisplayNodes()
```

## Acknowledgments

Cleaver is an Open Source software project that is principally funded through the SCI Institute's NIH/NIGMS CIBC Center. Please use the following acknowledgment and send references to any publications, presentations, or successful funding applications that make use of NIH/NIGMS CIBC software or data sets to <a href="http://www.sci.utah.edu/software/cleaver.html">SCI</a>: "This project was supported by the National Institute of General Medical Sciences of the National Institutes of Health under grant number P41 GM103545-18."


TetGen citation: Si, Hang (2015). "TetGen, a Delaunay-based Tetrahedral Mesh Generator". ACM Transactions on Mathematical Software. 41 (2): 11:1-11:36. doi:10.1145/2629697
