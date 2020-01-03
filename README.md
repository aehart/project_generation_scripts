# Project Generation Scripts

Basic instructions to run the project generation for the Vivado HLS project with hourglass configuration

## Overview of scripts for producing wiring files.

(More technical details about the internal operation of the scripts can be found at end of this document).

* The master configuration file for hourglass project is generated by
		
      ./HourGlassConfig.py
    
  The default output file is *wires.input.hourglassExtended*.

  **DATA FORMAT**: Each line in the output file contains a instance of a processing module as well as all its input and output memories. The input memories, the processing module, and the output memories are separated by ">":

       InMem1 InMem2 ... > ProcessModuleX > OutMem1 OutMem2 ...

  The names of the output memories are unique, such that none is written by > 1 proc module to avoid conflicts. (The script does not prevent input memories being read by > 1 proc module, but this is fixed by WiresLongVM.py).

* Create modules and wiring .dat files (despite name, this is for official Tracker geom).

      ./WiresLongVM.py wires.input.hourglassExtended

  This script parses the configuration file generated from the previous step and converts it to three output files: 
  *wires.dat*, *memorymodules.dat*, *processingmodules.dat* & *processingmodules_input.dat* (not used).

  These three .dat files contain more or less the same information as the master config file but are reformated for more convenient access in emulation software and later steps. However, if the script detects that a memory is read by > 1 proc module, it clones it to avoid conflicts, appending an index to its name to distinguish these clones. Furthermore, it names the input/output pins used in the proc module.

  **DATA FORMAT**: In *memorymodules.dat* and *processingmodules.dat* list all memories/proc modules, with each line containing a module instance name and its corresponding type, following the format

      ModuleType: ModuleInstance

  In wires.dat, all memories are listed, one per line, giving also the name of the proc block (and its pin name after ".") that connect to the memory's input/output port.

  (*FIXME*: for memorymodules.dat, there is a third column (e.g. "[36]") that is supposed to indicate the data width of the memory. This number is hardcoded and is likely out of date. It is not used in the later steps for generating top level project, but is used to estimate RAM useage. It may be less confusing if we either remove it or update the numbers or link it to the corresponding HLS memory header files.)
  
* Generate the top function for Vivado HLS (in HLS or HDL)

  (Currently CANNOT generate a full project since some processing steps are under construction)

      1) Checkout L1Trk HLS code (https://github.com/cms-tracklet/firmware-hls) into a new directory
      2) Ensure ROOT is in your PATH.
      3 - for HLS) ./generator_vhls.py <L1Trk HLS firmware directory>
      OR
      3 - for Verliog) ./generator_verilog.py <L1Trk HLS firmware directory>
      
  Optional arguments include:
  
      -h, --help          For help
  
      -f, --topfunc       Top function name
      -n, --projname      Project name
      -p, --procconfig    Name of the processing module configuration .dat file
      -m, --memconfig     Name of the memory module configuration .dat file
      -w, --wireconfig    Name of the wiring configuration .dat file
      --memprint_dir      Directory to search for memory printouts produced by the emulation
      --emData_dir        Directory into which the memory printout files are copied for the HLS project
      
      For generating a partial project:
      -r, --region        Detector region of the generated project.
      		              Choose from A(all), L(barrel), D(disk).
      --uut               Specify a unit under test, e.g. TC_L1L2E
      -u, --nupstream     The number of processing steps to be generated upstream of the UUT 
      -d, --ndownstream   The number of processing steps to be generated downstream of the UUT

  This script parses the three .dat files from the previous step and instantiates a TrackletGraph object (defined in TrackletGraph.py).
  The TrackletGraph object is a representation of the project configuration, containing all processing and memory objects as well as their inter-connections.

  The other part of this script takes the TrakletGraph object as inputs and writes out relevant files for the top level project.
  In order to generate correct and up-to-date functions for relevant processing steps, the script looks for and parses the function definitions in the corresponding header files in L1Trk HLS repo (https://github.com/cms-tracklet/firmware-hls/tree/master/TrackletAlgorithm).

  HLS: The final product of this script includes source and header files for the HLS top function, a test bench file, and a tcl script to generate the Vivado HLS project. A diagram presenting the generated project is also produced.
  In addition, the script tries to select and copy necessary memory printout files, if available, from the emulation to be used in the test bench of the Vivado HLS project.

  HDL: The final product of this script includes a top-level verilog module which instantiates all the relevant HLS processing blocks and verilog memory modules, as well as a verilog test bench. In the future, the script will generate a tcl script needed to generate the project.
  In addition, like the HLS version, the script tries to select and copy necessary memory printout files, if available, from the emulation to be used in the test bench of the Vivado HLS project (this feature is currently broken for the verilog version, but it will be fixed).

-----------------------------------------------------------------

## Scripts for plotting wiring:

* Prepare files for graph generation:

      ./Graph.py

* Make graph in root:

      root -l
      root[0] .L DrawTrackletProject.C++
      root[1] DrawTrackletProject()

* You can also generate the 'zoomed in' views of all the processing modules
after running the WiresLongVM.py script by doing

      ./generatesubgraphs

-----------------------------------------------------------------

## Technical details of scripts for producing wiring files.

### ./HourGlassConfig.py

N.B. This documentation describes the prompt tracking steps, but indicates where they differ
for displaced tracking.

-- Configuration parameters:

Set at top of script. e.g. "nallstubslayers" sets number of coarse phi regions (each corresponding to an "AllStub" memory) each layer is divided into within a phi nonant. And "nvmtelayers" sets the number of Virtual Modules in phi per coarse phi region for each layer, for later used by TrackletEngine.

This writes FILE = wires.input.hourglassExtended . Documenting how each section of this is produced:

1) "Input Router" ("IL") 

Each sends stubs from one DTC (e.g. "PS10G_1") to 4-8 AllStub memories (labelled "PHIA-PHIH", each corresponding to a coarse phi division of nonant) in each layer ("L1-L6" or "D1-D5") the DTC reads.
It's output AllStub memories therefore have names such as "IL_L1PHIC_PS10G_1_A".

findInputLinks() reads a file "dtcphirange.txt" (written by C++ emulation), which has a line for each 
DTC indicating its name and the range of phi of stubs it reads. This is used to identify which DTCs
map on to which coarse phi regions. 

N.B. FILE contains no section listing the IL itself and its connections to the DTCs.

2) "VMRouters (VMR) for the TEs in the layers / disks"

e.g. IL_L1PHIC_PS10G_1_A IL_L1PHIC_PS10G_2_A IL_L1PHIC_neg_PS10G_1_A > VMR_L1PHIC > AS_L1PHIC VMSME_L1PHIC9 VMSME_L1PHIC10 VMSME_L1PHIC11 VMSME_L1PHIC12 VMSTE_L1PHIC9 VMSTE_L1PHIC10 VMSTE_L1PHIC11 VMSTE_L1PHIC12 VMSTE_L1PHIZ5 VMSTE_L1PHIZ6

Each VMR writes AllStub memories ("AS_") for a single coarse phi region (e.g. "PHIC"), merging data from all DTCs related to this phi region. It does so by merging data from the AllStub memories written by all ILs for this phi region. Above FILE line lists all IL AllStub Memories that feed (">") into a single VMR ("VMR_L1PHIC") that writes to the output AllStub memories ("AS_L1PHIC").

Each VMR also writes to Virtual Module memories ("VMS") to be used later by the Match Engine ("ME") or "Tracklet Engine ("TE"). e.g. In FILE word "VMSTE_L1PHIC9 - 12", we are writing to the 9th - 12th VM in L1. (Each coarse phi region in L1 currently has 4 VMs (cfg param "nvmtelayers"), so PHIC contains VMs 9-12).

3) "Tracklet Engines (TE) for seeding layer / disk"

Each TE reads one VM in two neighbouring layers, finds stub pairs and writes them to a StubPair ("SP") memory.

e.g. VMSTE_L1PHIB5 VMSTE_L2PHIA7 > TE_L1PHIB5_L2PHIA7 > SP_L1PHIB5_L2PHIA7

indicates VMs PHIB5 from L1 and PHIA7 from L2 are processed by TE with name corresponding to these VMs,
and written to corresponding SP memory.

validtepair*(...) checks of each VM pair would be consistent with a track of Pt > 2 GeV.

For displaced tracking, function validtedpair*(...) used instead, which requires the VM pair to be consistent with |d0| < 3cm for at least one of abs(q/Pt) = 1/2 or -1/2.

4) "Tracklet Calculators (TC) for seeding layer / disk"

e.g. SP_L1PHIB6_L2PHIA8 SP_L1PHIB7_L2PHIA5 SP_L1PHIB7_L2PHIA6 > TC_L1L2C > TPAR_L1L2XXC TPROJ_L1L2XXC_L3PHIA TPROJ_L1L2XXC_L3PHIB TPROJ_L1L2XXC_L4PHIA

Each TC reads several SP memories, each containing a pair of VMs of two seeding layers (L1 & L2 here). Several (set by "tcs") TCs are created for each layer pair, and the SP memories are distributed between them. In TC_L1L2C, "C" indicates that this is 3rd TC in the layer pair. (N.B. Completely unrelated to the coarse phi regions). The helix params are stored in memory TPAR_L1L2XXC, (with "XX" added to name of all TC output memories). The track projections to all other layers are stored in TPROJ_L1L2XXC_L3PHIA etc, where last part of name indicates layer number and coarse phi region of projection. (N.B. These coarse phi regions can differ from those of VMRs).

phiprojrange*(...) is used to determine phi projection in each layer, to identify which coarse phi regions are consistent with projection.

This step also stores the list of all TPAR & TPROJ memories in arrays TPROJ_list & TPAR_list.

5) "PROJRouters for the MEs in layer / disk"

TPROJ_L3L4XXA_L2PHIA TPROJ_L3L4XXB_L2PHIA TPROJ_L3L4XXC_L2PHIA > PR_L2PHIA > AP_L2PHIA VMPROJ_L2PHIA1 VMPROJ_L2PHIA2 

e.g. This merges all projections (e.g. TPROJ_L3L4XXB_L2PHIA, seed L3L4 extrapolated to coarse phi region A of L2 (L2PHIA) using the B'th tracklet calculator) that point to the same coarse phi region of the extrapolation layer from various seeding layers. This list of these is taken from array TPROJ_list, mentioned above. These are all processed by a single Projection Router algo. It writes intercept point of helix with coarse phi region to All Projection (AP) memory. And whenever intercept lies within a VM, (although code doesn't check this, only if intercept is consistent with coarse phi region), writes index of tracklet to  VM Projection (VMProj) memory for that VM.

6) "Match Engines for the layers / disks"

VMSME_L1PHIA1 VMPROJ_L1PHIA1 > ME_L1PHIA1 > CM_L1PHIA1

Checks consistency of stubs in VM with helix intercept. e.g. ME for VM A1 in L1 reads stubs from VM memory (VMS) and intercepts from projection memory (VMPROJ) for this VM. Matching (tracklet,stub) indices written to CandidateMatch (CM) memory.

7) "Match Calculator for layer / disk"

CM_L2PHIB9 CM_L2PHIB10 CM_L2PHIB11 > MC_L2PHIB > FM_L3L4XX_L2PHIB FM_L5L6XX_L2PHIB

More precise pairing of stubs & intercepts within a given coarse phi region "B" of a layer L2, using the Candidate Matches of all VMs in that region. Result written to Full Match (FM") memories, subdivided according to the seeding layer pairs (e.g. L3L4, where "XX means nothing") which can be extrapolated to the extrapolation layer.

8) "Tracklet Fit for seeding" 

FM_L5L6XX_L1PHIA FM_L5L6XX_L1PHIB FM_L5L6XX_L1PHIC > FT_L5L6XX > TF_L5L6XX

A fit algo is run for each seeding layer pair. It reads the matches (FM) of stubs to tracklets from each layer and all coarse phi regions.

### ./WiresLongVM.py

N.B. HourGlassConfig.py ensures that no output memory is written by > 1 proc module, to avoid conflicts. However, it doesn't ensure that no input memory is read by > 1 proc module, so this must be fixed by WiresLongVM.py. It does this by cloning the memories if they are read by > 1 proc module, (appending "n1", "n2" etc. to their name to identify each clone); and then using several output pins of the proc module that writes to this memory, with each pin writing to one clone of the memory. Furthermore, as wires.input.hourglassExtended indicates that each proc block reads/writes several memories, and a different pin of proc block must be used for each, this script names the pins (after "." in the module name).

a) Reads file wires.input.hourglassExtended (written by HourGlassConfig.py) showing which processing blocks are connected to which input & output memories.

b) Writes file processingmodules_inputs.dat (never used!?) showing number of input memories connected to each proc step. e.g.

VMR_D3PHIB  has 6 inputs

gives #inputs to VMRouter "D3PHIB" (naming convention given above under HourGlassConfig.py).

c) Writes file processingmodules.dat listing all processing blocks, and the generic algo step each corresponds to. e.g.

VMRouter: VMR_D3PHIB

d) Writes file memorymodules.dat.

VMStubsTE: VMSTE_L5PHIA1n1 [18]
VMStubsTE: VMSTE_L5PHIA1n2 [18]

listing all input memories (naming convention given above under HourGlassConfig.py) with "n2" etc. appended to their names, if multuple copies of a given memory are needed (to avoid conflicts if it is read by multiple proc blocks) indicating which copy it is. The string "VMEStubsTE:" just indicates the generic memory type (e.g. VM memory to be used by TE). The string "[18]" indicates assumed the data word width, hard-wired in the script, which should correspond to https://twiki.cern.ch/twiki/bin/view/CMS/HybridDataFormat .

e) Writes file wires.dat.

VMSTE_L1PHIA4n2 input=> VMR_L1PHIA.vmstuboutPHIA4n2  output=> TE_L1PHIA4_L2PHIA3.innervmstubin

Says that memory VMSTE_L1PHIA4 is written by algo step VMR_L1PHIA (naming convention given above under HourGlassConfig.py). Here "n2" in memory name indicates that this is the second copy of the memory (where multiple copies used to avoid conflicts); ".vmstuboutphiA4n2" & ".innervmstubin" are a unique name given to the pin of the processing block that writes/reads this memory.
