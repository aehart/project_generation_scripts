import os,sys

# Define the module class with all the properties
class Module:
    def __init__(self):
        self.module = None
        self.name = None # Names defined in the DN
        self.inputs = None # In and out from master wires file
        self.outputs = None
        self.in_names = None # In and out names should be consistent with Verilog modules
        self.out_names = None
        self.common = None
        self.parameters = '' # Each module has unique parameters
        self.size = 0 # Memory sizes for connecting wires
        self.start = '' 
        self.done = ''

# Read the processing modules
if len(sys.argv) > 1:
    region = sys.argv[1]
else:
    print 'Region to process needed. Try "D3" and run again'
    sys.exit()
# Run the other scripts from here
os.system('python SubProject.py '+region)
os.system('python Wires.py wires.'+region)

f = open('processingmodules_'+region+'.dat')
modules = []
for line in f:
    signals = [] # Pair with nice name and specific instance name
    signals.append(line.split(':')[0])
    signals.append(line.split(':')[1].strip())
    modules.append(signals) # Add to the list of pairs

# Read the memory modules
g = open('memorymodules_'+region+'.dat')
memories = []
for line in g:
    signals = [] # Nice name, instance name, memory size
    signals.append(line.split(':')[0])
    signals.append(line.split(':')[1].split(' ')[1].strip())
    if len(line.split(':')[1].split(' '))>2:
        signals.append(int(line.split(':')[1].split(' ')[-1].replace('[','').replace(']','').strip()))
    memories.append(signals) # Add to the list of triplets

# Common signals for every module # IPBus might go away
Common = '.clk(clk),\n.reset(reset),\n.en_proc(en_proc)'

# Read initial lines of Tracklet_processing
# Define inputs, outputs and start/done signals
p = open('prologue.txt')
#if "D5" in region:
#  p = open('prologue_disk.txt')
#else:
#  p = open('prologue.txt')
prologue = []
for line in p:
    prologue.append(line)
# Read final lines for IPbus and possible reader
if "D5" in region:
  ep  = open('epilogue_disk.txt')
else:
  ep  = open('epilogue.txt')
epilogue = []
for line in ep:
    epilogue.append(line)

string_prologue = ''
string_starts = ''
string_memories = ''
string_processing = ''
string_epilogue = ''
####################################################
####################################################

il = 0

# Always write the initial lines
for p in prologue:
    string_prologue += '\n' +  p.strip()
    
# Start looping over the memories first
for x in memories:
    h = open('wires_'+region+'.dat') # Open the wire connections file
    m = Module() # Create a module
    i = [] # List of inputs
    i_n = [] # List of input names
    o = [] # List of outputs
    o_n = [] # List of output names
    m.module = x[0] # Module nice name from memory list
    m.name = x[1]  # Module instance name from memory list
    if len(x)>2: # If triplet, get the memory size
        m.size = x[2]
    for line in h: # Loop over connections
        if line.split(' ')[0] == x[1]:  # If instance corresponds to current memory
            if len(line.split(' ')[2].split('.')) > 1: # Memory has inputs
                i.append(line.split(' ')[2].split('.')[0]+'_'+x[1]) # Add input to module's list
                i.append(line.split(' ')[2].split('.')[0]+'_'+x[1]+'_wr_en') # Memory inputs usually have a write enable
                i_n.append('data_in') # Names defined in Verilog memory module
                i_n.append('enable')
            if len(line.split(' ')[-1].split('.')) > 1: # Memory has outputs
                o.append(x[1]+'_'+line.split(' ')[-1].split('.')[0]+'_number') # Number of items in memory that goes to processing module
                o.append(x[1]+'_'+line.split(' ')[-1].split('.')[0]+'_read_add')
                o.append(x[1]+'_'+line.split(' ')[-1].split('.')[0])
                o_n.append('number_out') # Names defined in Verilog memory module
                o_n.append('read_add')
                o_n.append('data_out')
    # Define the properties of the module
    m.inputs = i
    m.outputs = o
    m.in_names = i_n
    m.out_names = o_n
    m.common = Common
    ####################################################
    # Specific properties of the memories
    # Any new memories added here
    ####################################################
    if m.module == 'InputLink':
        il +=  1
        m.outputs = [m.outputs[-1]] # This memory has been gutted and is now a passthrough
        m.in_names.append('data_in1') # Two inputs from the links stiched together
        m.in_names.append('data_in2')
        m.inputs.append('input_link%d_reg1'%il)
        m.inputs.append('input_link%d_reg2'%il)
        m.inputs.append(m.outputs[-1]+'_read_en')
        m.out_names = [m.out_names[-1]]
        m.in_names.append('read_en')
        m.out_names.append('empty')
        m.outputs.append(m.outputs[-1]+'_empty')
        m.common = m.common.replace('//.reset(','.reset(')
    if m.module == 'StubsByLayer':
        m.start = m.inputs[0].replace(m.name,'')+'start'
        m.done = m.name+'_start'
        seen_done1_5 = True
    if m.module == 'StubsByDisk':
        m.start = m.inputs[0].replace(m.name,'')+'start'
        m.done = m.name+'_start'
        seen_done1_5 = True
    if m.module == 'AllStubs':
        m.out_names = m.out_names[1:] # These memories don't have to send number out
        m.outputs = m.outputs[1:] # They are accessed directly by TC and MC
        m.start = m.inputs[0].replace(m.name,'')+'start'
        if 'MC' in m.outputs[0]:
            m.out_names = ['read_add_MC','data_out_MC'] # If the memory is read by an MC change the output names # TODO not needed anymore
    if m.module == 'VMStubs':
        m.start = m.inputs[0].replace(m.name,'')+'start'
        m.done = m.name+'_start'
        seen_done2_5 = True
        if 'ME' in m.outputs[0]:
            m.parameters = '#("Match")'
        else:
            m.parameters = '#("Tracklet")'
    if m.module == 'StubPairs':
        m.start = m.inputs[0].replace(m.name,'')+'start'
        m.done = m.name+'_start'
        seen_done3_5 = True
    if m.module == 'TrackletParameters':
        m.out_names = m.out_names[1:] # These memories don't have to send number out
        m.outputs = m.outputs[1:]
        m.start = m.inputs[0].replace(m.name,'')+'start'
    if m.module == 'TrackletProjections':
        #if 'From' not in m.name:
        #    m.start = 'startproj5_0' # Projections from neighbors start later
        #else:
        #    m.start = 'start6_0'
        #if 'ToPlus' in m.name or 'ToMinus' in m.name:
	    #m.done = '' if seen_done4_5 else 'done4_5'
        #    seen_done4_5 = True
        #if 'FromPlus'in m.name or 'FromMinus' in m.name:
        #    m.done = '' if seen_done5_5 else 'done5_5'
        #    seen_done5_5 = True
        m.start = m.inputs[0].replace(m.name,'')+'proj_start'
        if 'From' in m.name:
            m.start = m.start.replace('proj_','')
        m.done = m.name+'_start'
    if m.module == 'AllProj':
        if 'L4D' in m.name or 'L5D' in m.name or 'L6D' in m.name:
            m.parameters = "#(1'b0)"
        m.out_names = m.out_names[1:] # These memories don't have to send number out
        m.outputs = m.outputs[1:]
        m.start = m.inputs[0].replace(m.name,'')+'start'
    if m.module == 'VMProjections':
        m.start = m.inputs[0].replace(m.name,'')+'start'
        m.done = m.name+'_start'
        seen_done6_5 = True
    if m.module == 'CandidateMatch':
        m.start = m.inputs[0].replace(m.name,'')+'start'
        m.done = m.name+'_start'
        seen_done7_5 = True
    if m.module == 'FullMatch':        
        m.out_names.append('read_en')
        if 'From' in m.name:
            m.parameters = "#(128)"
            #m.start = 'start10_0' # Matches from neighbors start later
            #m.done = '' if seen_done9_5 else 'done9_5'
            seen_done9_5 = True
            m.outputs.append(m.outputs[-1]+'_read_en')
        elif 'To' in m.name:
            m.parameters = "#(128)"
            #m.start = 'start9_0'
            m.outputs.append("1'b1")
        else:
            #m.start = 'start9_0'
            #m.done = '' if seen_done8_5 else 'done8_5'
            seen_done8_5 = True
            m.outputs.append(m.outputs[-1]+'_read_en')
        m.start = m.inputs[0].replace(m.name,'')+'start'
        m.done = m.name+'_start'
    if m.module == 'TrackFit':
        m.outputs.append(m.name+'_DataStream') # Final track out, going to DTC but should go to DuplicateRemoval
        m.out_names.append('data_out')
        m.start = m.inputs[0].replace(m.name,'')+'start'
        m.done = m.name+'_start'
        seen_done10_5 = True
    ####################################################
    if('mem' not in sys.argv): # If you want memories in the print out
        string_memories += '\n'
        for i in m.inputs: # Declare the wires to be used in the memory
            if 'input_link' not in i: # Input link memory does not have an enable
                if '_en' in i:
                    string_memories += '\n' +  'wire '+i+';'
                else:
                    string_memories += '\n' +  'wire ['+str(m.size-1)+':0] '+i+';' # Size of the wire
        for o in m.outputs: # Declare the wires to be used in the memory
            if 'empty' in o or 'TF_' in o: # Not needed wires
                string_memories += '\n' +  '//wire '+o+';'
            elif 'number' in o:
                string_memories += '\n' +  'wire [5:0] '+o+';' # Number of objects in memory
            elif 'read' in o:
                if m.module == 'VMStubs' or m.module == 'AllStubs' or m.module == 'TrackletParameters' : # These memories have to cross the link
                    string_memories += '\n' +  'wire [10:0] '+o+';' # Deeper for latency
                elif m.module == 'TrackletProjections' or m.module == 'FullMatch': # Not as deep
                    if '_en' in o:
                        string_memories += '\n' +  'wire '+o+';'
                    else:
                        string_memories += '\n' +  'wire [9:0] '+o+';'
                else:
                    string_memories += '\n' +  'wire [8:0] '+o+';' # Standard depth 6 bits of number plus 3 of BX
                #print 'wire [5:0] '+o+';'
            elif "1'b1" in o:
                continue
            else:
                string_memories += '\n' +  'wire ['+str(m.size-1)+':0] '+o+';' # Wire size
        string_memories += '\n' +  m.module + ' ' + m.parameters +  ' ' + m.name + '(' # Parameters here
        for n,i in zip(m.in_names,m.inputs): # Loop over signals and names
            string_memories += '\n' +  '.'+n+'('+i+'),'
        for n,o in zip(m.out_names,m.outputs):
            string_memories += '\n' +  '.'+n+'('+o+'),'
        string_memories += '\n' +  '.start('+m.start+'),'
        string_memories += '\n' +  '.done('+m.done+'),'
        string_memories += '\n' +  m.common
        string_memories += '\n' +  ');'

####################################################
####################################################
# Done is only needed for 1 module
# If seen once, don't add it anymore
seen_done1_0 = False
seen_done2_0 = False
seen_done3_0 = False
seen_done4_0 = False
seen_done_proj = False
seen_done5_0 = False
seen_done6_0 = False
seen_done7_0 = False
seen_done8_0 = False
seen_done9_0 = False
seen_done10_0 = False

# Start looping over the processing modules
for x in modules:
    h = open('wires_'+region+'.dat') # Open the wire connections file
    m = Module() # Create a module
    i = [] # List of inputs
    i_n = [] # List of input names
    o = [] # List of outputs
    o_n = [] # List of output names
    m.module = x[0] # Module nice name from processing list
    m.name = x[1]  # Module instance name from processing list
    for line in h: # Loop over connections
        if line.split(' ')[-1].strip().split('.')[0] == x[1]: # If instance corresponds to current processing
            i.append(line.split(' ')[0]+'_'+x[1]) # Add input to module's list
            i_n.append(line.split(' ')[-1].strip().split('.')[1])
        if line.split(' ')[2].strip().split('.')[0] == x[1]:
            o.append(x[1]+'_'+line.split(' ')[0]) # Add output to module's list
            o_n.append(line.split(' ')[2].strip().split('.')[1])
    # Define the properties of the module
    m.inputs = i
    m.outputs = o
    m.in_names = i_n
    m.out_names = o_n
    m.common = Common
    ####################################################
    # Specific properties of the processing modules
    # Any new processing added here
    ####################################################
    if m.module == 'LayerRouter':
        m.start = m.inputs[0].replace(m.name,'')+'start'
        m.done = m.name+'_start'
        seen_done1_0 = True
        out_names = []
        outputs = []
        for cnt,out in enumerate(m.outputs):
            out_names.append(str('wr_en%d' %(cnt+1))) # Write enable for every layer
            outputs.append(out+'_wr_en')
        #print out_names
        m.out_names = m.out_names + out_names
        m.outputs = m.outputs + outputs
    if m.module == 'VMRouter':
        enables = []
        enables_2 = []
        for o in m.out_names: 
            if 'vmstubout' in o:
                enables.append(o+'_wr_en') # For every output name create a write enable name
        for o in m.outputs:
            if 'VMR' in o and 'VMS' in o: # Output going to VMStub memory
                enables_2.append(o+'_wr_en') # For every output create a write enable
        m.out_names = m.out_names + enables
        m.outputs = m.outputs + enables_2
        if 'L1' in m.name or 'L3' in m.name or 'L5' in m.name: # Odd layer parameters
            if 'L1' in m.name or 'L3' in m.name: # Inner layer parameter
                m.parameters = "#(1'b1,1'b1)"
            else:
                m.parameters = "#(1'b0,1'b1)"
        elif 'F2' in m.name or 'F4' in m.name or 'B2' in m.name or 'B4' in m.name:
            m.parameters = "#(1'b1,1'b0,1'b0)"
        elif 'F1' in m.name or 'F3' in m.name or 'F5' in m.name or'B1' in m.name or 'B3' in m.name or 'B5' in m.name:
            m.parameters = "#(1'b1,1'b1,1'b0)"
        else:
            if 'L2' in m.name:
                m.parameters = "#(1'b1,1'b0)"
            else:
                m.parameters = "#(1'b0,1'b0)"

        m.start = m.inputs[0].replace(m.name,'')+'start'
        m.done = m.name+'_start'
        seen_done2_0 = True
        vs = 0
        valids = []
        valids2 = []
        for o in m.outputs:
            if 'VMR_L' in o and '_AS_L' in o: # Output going to AllStub memory
                vs = vs + 1
                valids.append(o+'_wr_en')
                valids2.append('valid_data%d'%vs)
            elif 'VMRD_F' in o and '_AS_F' in o: # Output going to AllStub memory
                vs = vs + 1
                valids.append(o+'_wr_en')
                valids2.append('valid_data%d'%vs)
            elif 'VMRD_B' in o and '_AS_B' in o: # Output going to AllStub memory
                vs = vs + 1
                valids.append(o+'_wr_en')
                valids2.append('valid_data%d'%vs)
        m.outputs = m.outputs + valids
        m.out_names = m.out_names + valids2
    if m.module == 'TrackletEngine':
        m.out_names.append('valid_data')
        m.outputs.append(m.outputs[0]+'_wr_en')
        m.start = m.inputs[0].replace(m.name,'')+'start'
        m.done = m.name+'_start'
        seen_done3_0 = True
	if 'TE_F' in m.name or 'TE_B' in m.name:
            m.parameters = '#("TETable_%s_phi.txt","TETable_%s_z.txt",'"1'b0"')'%(m.name,m.name) # TE Tables names have to be in this format. CHECK EMULATION
	else:
            m.parameters = '#("TETable_%s_phi.txt","TETable_%s_z.txt")'%(m.name,m.name) # TE Tables names have to be in this format. CHECK EMULATION
    if m.module == 'TrackletCalculator':
        for i,n in enumerate(m.in_names): # Count the inputs
            if 'stubin' in n:
                m.in_names.insert(len(m.in_names),m.in_names.pop(i)) # Move the AllProjections to the back
        for i,n in enumerate(m.inputs): # Count the inputs
            if 'AS_' in n:
                m.inputs.insert(len(m.inputs),m.inputs.pop(i)) # Move the AllProjections to the back
        ons = []
        for o in m.out_names:
            ons.append('valid_'+o)
        m.out_names = m.out_names + ons
        m.out_names = m.out_names + ['done_proj'] # Done signal for projections
        seen_done_proj = True
        outs = []
        for o in m.outputs:
            outs.append(o+'_wr_en')
        m.outputs = m.outputs+outs
        m.outputs = m.outputs+[m.name+'_proj_start'] # Hardcoded signal name
        TC_index = ''
        if 'L1' in m.name:
            if 'D3L2D3' in m.name:
                TC_index = "4'b0000"
            if 'D3L2D4' in m.name:
                TC_index = "4'b0001"
            if 'D4L2D4' in m.name:
                TC_index = "4'b0010"
            m.parameters = '#("InvRTable_TC_L1D3L2D3.dat",'+"`TC_L1L2_krA,`TC_L1L2_krB,1'b1,1'b1,"+TC_index+")"
        if 'L3' in m.name:
            if 'D3L4D3' in m.name:
                TC_index = "4'b0000"
            if 'D3L4D4' in m.name:
                TC_index = "4'b0001"
            if 'D4L4D4' in m.name:
                TC_index = "4'b0010"
            m.parameters = '#("InvRTable_TC_L3D3L4D3.dat",'+"`TC_L3L4_krA,`TC_L3L4_krB,1'b1,1'b0,"+TC_index+")"
        if 'L5' in m.name:
            if 'D3L6D3' in m.name:
                TC_index = "4'b0000"
            if 'D3L6D4' in m.name:
                TC_index = "4'b0001"
            if 'D4L6D4' in m.name:
                TC_index = "4'b0010"            
            m.parameters = '#("InvRTable_TC_L5D3L6D3.dat",'+"`TC_L5L6_krA,`TC_L5L6_krB,1'b0,1'b0,"+TC_index+")"
        m.start = m.inputs[0].replace(m.name,'')+'start'
        m.done = m.name+'_start'
        seen_done4_0 = True
    if m.module == 'TrackletDiskCalculator':
        for i,n in enumerate(m.in_names): # Count the inputs
            if 'stubin' in n:
                m.in_names.insert(len(m.in_names),m.in_names.pop(i)) # Move the AllProjections to the back
        for i,n in enumerate(m.inputs): # Count the inputs
            if 'AS_' in n:
                m.inputs.insert(len(m.inputs),m.inputs.pop(i)) # Move the AllProjections to the back
        ons = []
        for o in m.out_names:
            ons.append('valid_'+o)
        m.out_names = m.out_names + ons    
        #if not seen_done_proj:    
        m.out_names = m.out_names + ['done_proj'] # Done signal for projections
        seen_done_proj = True
        outs = []
        for o in m.outputs:
            outs.append(o+'_wr_en')
        m.outputs = m.outputs+outs
        m.outputs = m.outputs+[m.name+'_proj_start'] # Hardcoded signal name
        #m.outputs = m.outputs+['done_proj4_0']
	diskTC_index = ''
	if 'F1' in m.name:
	    if 'D5F2D5' in m.name:
		diskTC_index = "4'b0100" 
            m.parameters = '#(0,"InvRTable_TC_F1D5F2D5.dat","InvTTable_TC_F1D5F2D5.dat",'+diskTC_index+")"#,981,1515,2341,2778,512)' # Parameter string for possible LUT file
	if 'F3' in m.name:
	    if 'D5F4D5' in m.name:
		diskTC_index = "4'b0100"
            m.parameters = '#(0,"InvRTable_TC_F3D5F4D5.dat","InvTTable_TC_F3D5F4D5.dat",'+diskTC_index+")"#,981,1515,2341,2778,512)' # Parameter string for possible LUT file
        #m.parameters = '#(47,17,"",981,1515)' # Parameter string for possible LUT file
        m.start = m.inputs[0].replace(m.name,'')+'start'
        m.done = m.name+'_start'
        seen_done4_0 = True
    if m.module == 'ProjectionTransceiver':
        ons = []
        for i,o in enumerate(m.out_names): # Count the outputs
            ons.append(o+'_%d'%(i+1)) # Enumerate them
        for i,o in enumerate(m.out_names):
            ons.append('valid_%d'%(i+1)) # Valid outputs
        m.out_names = ons        
        valids = []
        for o in m.outputs:
            valids.append(o+'_wr_en')
        m.outputs = m.outputs + valids
        ins = []
        for i,o in enumerate(m.in_names): # Count the inputs
            ins.append(o+'_%d'%(i+1)) # Enumerate them
        m.in_names = ins
        m.start = m.inputs[0].replace(m.name,'')+'start'
        m.done = m.name+'_start'
        seen_done5_0 = True
        m.out_names = m.out_names+['valid_proj_data_stream','proj_data_stream'] # Outputs to links
        m.in_names = m.in_names+['incomming_proj_data_stream'] # Input from links
        m.outputs = m.outputs+[m.name+'_To_DataStream_en',m.name+'_To_DataStream']
        m.inputs = m.inputs+[m.name+'_From_DataStream']
        if 'L1L2' in m.name:
            m.parameters = '#(0)'
        elif 'L3L4' in m.name:
            m.parameters = '#(1)'
        if 'L5L6' in m.name:
            m.parameters = '#(2)'
        
    if m.module == 'ProjectionRouter':
        m.outputs.append(m.outputs[-1]+'_wr_en') # Write enable signal to AllProjection memory
        m.out_names.append('valid_data')
        m.outputs = m.outputs + [x+'_wr_en' for x in m.outputs[:-2]] # Write enable to VMProjection memory
        m.out_names = m.out_names + [x+'_wr_en' for x in m.out_names[:-2]]
        if 'PR_L1' in m.name or 'PR_L3' in m.name: # Inner odd parameters
            m.parameters = "#(1'b1,1'b1)"
        elif 'PR_L2' in m.name:
            m.parameters = "#(1'b0,1'b1)"
        elif 'PR_L4' in m.name or 'PR_L6' in m.name: # Outer even parameters
            m.parameters = "#(1'b0,1'b0)"
        elif 'PR_L5' in m.name:
            m.parameters = "#(1'b1,1'b0)"
        elif 'PRD' in m.name:
            if 'PRD_F1' in m.name or 'PRD_F3' in m.name or 'PRD_F5' in m.name:
                m.parameters = "#(1'b1,1'b0,1'b0)"
            if 'PRD_F2' in m.name or 'PRD_F4' in m.name:
                m.parameters = "#(1'b0,1'b0,1'b0)"
        m.start = m.inputs[0].replace(m.name,'')+'start'
        m.done = m.name+'_start'
        seen_done6_0 = True
    if m.module == 'MatchEngine':
        m.outputs.append(m.outputs[0]+'_wr_en') 
        m.out_names.append('valid_data')
	if 'VMPROJ' in m.inputs[1]: #default
          m.start = m.inputs[1].replace(m.name,'')+'start'
          m.done = m.name+'_start'
	elif 'VMPROJ' in m.inputs[0]: #for F5 or B5 VMS is m.inputs[1] b/c these do not have TrackletEngines which change order of wires
          m.start = m.inputs[0].replace(m.name,'')+'start'
          m.done = m.name+'_start'
        seen_done7_0 = True
    if m.module == 'MatchCalculator':
        for i,n in enumerate(m.in_names): # Count the inputs
            if 'allprojin' in n:
                m.in_names.insert(len(m.in_names),m.in_names.pop(i)) # Move the AllProjections to the back
        for i,n in enumerate(m.inputs): # Count the inputs
            if 'AP_' in n:
                m.inputs.insert(len(m.inputs),m.inputs.pop(i)) # Move the AllProjections to the back

        for i,n in enumerate(m.in_names): # Count the inputs
            if 'allstubin' in n:
                m.in_names.insert(len(m.in_names),m.in_names.pop(i)) # Move the AllStubs and AllProjections to the back
        for i,n in enumerate(m.inputs): # Count the inputs
            if 'AS_' in n:
                m.inputs.insert(len(m.inputs),m.inputs.pop(i)) # Move the AllProjections to the back
        m.outputs.append(m.outputs[0]+'_wr_en') # Write enable for local and neighbor matches
        m.outputs.append(m.outputs[1]+'_wr_en')
        m.outputs.append(m.outputs[2]+'_wr_en')
        m.out_names.append('valid_matchminus')
        m.out_names.append('valid_matchplus')
        m.out_names.append('valid_match')
        if 'MC_L1L2_L3' in m.name: # Parameter for constants # Will be moved to header file
            m.parameters = "#(1'b1,`PHI_L3,`Z_L3,`R_L3,`PHID_L3,`ZD_L3,`MC_k1ABC_INNER,`MC_k2ABC_INNER,`MC_phi_L1L2_L3,`MC_z_L1L2_L3,`MC_zfactor_INNER)"
        if 'MC_L1L2_L4' in m.name:
            m.parameters = "#(1'b0,`PHI_L4,`Z_L4,`R_L4,`PHID_L4,`ZD_L4,`MC_k1ABC_OUTER,`MC_k2ABC_OUTER,`MC_phi_L1L2_L4,`MC_z_L1L2_L4,`MC_zfactor_OUTER)"
        if 'MC_L1L2_L5' in m.name:
            m.parameters = "#(1'b0,`PHI_L5,`Z_L5,`R_L5,`PHID_L5,`ZD_L5,`MC_k1ABC_OUTER,`MC_k2ABC_OUTER,`MC_phi_L1L2_L5,`MC_z_L1L2_L5,`MC_zfactor_OUTER)"
        if 'MC_L1L2_L6' in m.name:
            m.parameters = "#(1'b0,`PHI_L6,`Z_L6,`R_L6,`PHID_L6,`ZD_L6,`MC_k1ABC_OUTER,`MC_k2ABC_OUTER,`MC_phi_L1L2_L6,`MC_z_L1L2_L6,`MC_zfactor_OUTER)"
        if 'MC_L3L4_L1' in m.name:
            m.parameters = "#(1'b1,`PHI_L1,`Z_L1,`R_L1,`PHID_L1,`ZD_L1,`MC_k1ABC_INNER,`MC_k2ABC_INNER,`MC_phi_L3L4_L1,`MC_z_L3L4_L1,`MC_zfactor_INNER)"
        if 'MC_L3L4_L2' in m.name:
            m.parameters = "#(1'b1,`PHI_L2,`Z_L2,`R_L2,`PHID_L2,`ZD_L2,`MC_k1ABC_INNER,`MC_k2ABC_INNER,`MC_phi_L3L4_L2,`MC_z_L3L4_L2,`MC_zfactor_INNER)"
        if 'MC_L3L4_L5' in m.name:
            m.parameters = "#(1'b0,`PHI_L5,`Z_L5,`R_L5,`PHID_L5,`ZD_L5,`MC_k1ABC_OUTER,`MC_k2ABC_OUTER,`MC_phi_L3L4_L5,`MC_z_L3L4_L5,`MC_zfactor_OUTER)"
        if 'MC_L3L4_L6' in m.name:
            m.parameters = "#(1'b0,`PHI_L6,`Z_L6,`R_L6,`PHID_L6,`ZD_L6,`MC_k1ABC_OUTER,`MC_k2ABC_OUTER,`MC_phi_L3L4_L6,`MC_z_L3L4_L6,`MC_zfactor_OUTER)"
        if 'MC_L5L6_L1' in m.name:
            m.parameters = "#(1'b1,`PHI_L1,`Z_L1,`R_L1,`PHID_L1,`ZD_L1,`MC_k1ABC_INNER,`MC_k2ABC_INNER,`MC_phi_L5L6_L1,`MC_z_L5L6_L1,`MC_zfactor_INNER)"
        if 'MC_L5L6_L2' in m.name:
            m.parameters = "#(1'b1,`PHI_L2,`Z_L2,`R_L2,`PHID_L2,`ZD_L2,`MC_k1ABC_INNER,`MC_k2ABC_INNER,`MC_phi_L5L6_L2,`MC_z_L5L6_L2,`MC_zfactor_INNER)"
        if 'MC_L5L6_L3' in m.name:
            m.parameters = "#(1'b1,`PHI_L3,`Z_L3,`R_L3,`PHID_L3,`ZD_L3,`MC_k1ABC_INNER,`MC_k2ABC_INNER,`MC_phi_L5L6_L3,`MC_z_L5L6_L3,`MC_zfactor_INNER)"
        if 'MC_L5L6_L4' in m.name:
            m.parameters = "#(1'b0,`PHI_L4,`Z_L4,`R_L4,`PHID_L4,`ZD_L4,`MC_k1ABC_OUTER,`MC_k2ABC_OUTER,`MC_phi_L5L6_L4,`MC_z_L5L6_L4,`MC_zfactor_OUTER)"
        m.start = m.inputs[0].replace(m.name,'')+'start'
        m.done = m.name+'_start'
        seen_done8_0 = True
    if m.module == 'DiskMatchCalculator':
	m.parameters = '#("rDSS_LUT.dat")'
        for i,n in enumerate(m.in_names): # Count the inputs
            if 'allprojin' in n:
                m.in_names.insert(len(m.in_names),m.in_names.pop(i)) # Move the AllProjections to the back
        for i,n in enumerate(m.inputs): # Count the inputs
            if 'AP_' in n:
                m.inputs.insert(len(m.inputs),m.inputs.pop(i)) # Move the AllProjections to the back

        for i,n in enumerate(m.in_names): # Count the inputs
            if 'allstubin' in n:
                m.in_names.insert(len(m.in_names),m.in_names.pop(i)) # Move the AllStubs and AllProjections to the back
        for i,n in enumerate(m.inputs): # Count the inputs
            if 'AS_' in n:
                m.inputs.insert(len(m.inputs),m.inputs.pop(i)) # Move the AllProjections to the back
        m.outputs.append(m.outputs[0]+'_wr_en') # Write enable for local and neighbor matches
        m.outputs.append(m.outputs[1]+'_wr_en')
        m.outputs.append(m.outputs[2]+'_wr_en')
        m.out_names.append('valid_matchminus')
        m.out_names.append('valid_matchplus')
        m.out_names.append('valid_match')
        #if 'MC_L1L2_L3' in m.name: # Parameter for constants # Will be moved to header file
        #    m.parameters = "#(1'b1,`PHI_L3,`Z_L3,`R_L3,`PHID_L3,`ZD_L3,`MC_k1ABC_INNER,`MC_k2ABC_INNER,`MC_phi_L1L2_L3,`MC_z_L1L2_L3,`MC_zfactor_INNER)"
        m.start = m.inputs[0].replace(m.name,'')+'start'
        m.done = m.name+'_start'
        seen_done8_0 = True
    if m.module == 'MatchTransceiver':
        ons = []
        for i,o in enumerate(m.out_names): # Count the outputs
            ons.append(o)
        for i,o in enumerate(m.out_names):
            ons.append('valid_matchout%d'%(i+1))
        m.out_names = ons
        valids = []
        for o in m.outputs:
            valids.append(o+'_wr_en')
        m.outputs = m.outputs + valids
        m.start = m.inputs[0].replace(m.name,'')+'start'
        m.done = m.name+'_start'
        seen_done9_0 = True
        m.out_names = m.out_names+['valid_match_data_stream','match_data_stream'] # Output signals to links
        m.in_names = m.in_names+['incomming_match_data_stream'] # Input signals from links
        m.outputs = m.outputs+[m.name+'_To_DataStream_en',m.name+'_To_DataStream']
        m.inputs = m.inputs+[m.name+'_From_DataStream']        
    if m.module == 'FitTrack':
        for i,n in enumerate(m.in_names): # Count the inputs
            if 'tpar1' in n:
                m.in_names.insert(len(m.in_names),m.in_names.pop(i)) # Move the AllStubs and AllProjections to the back
        for i,n in enumerate(m.in_names): # Count the inputs
            if 'tpar2' in n:
                m.in_names.insert(len(m.in_names),m.in_names.pop(i)) # Move the AllStubs and AllProjections to the back
        for i,n in enumerate(m.in_names): # Count the inputs
            if 'tpar3' in n:
                m.in_names.insert(len(m.in_names),m.in_names.pop(i)) # Move the AllStubs and AllProjections to the back
        for i,n in enumerate(m.inputs):
            if 'TPAR' in n:
                m.inputs.insert(len(m.inputs),m.inputs.pop(i))
        for i,n in enumerate(m.inputs):
            if 'TPAR' in n:
                m.inputs.insert(len(m.inputs),m.inputs.pop(i))

        if 'L1L2' in m.name:
            m.parameters = '#("L1L2")'
        elif 'L3L4' in m.name:
            m.parameters = '#("L3L4")'
        elif 'L5L6' in m.name:
            m.parameters = '#("L5L6")'
                
        m.out_names.append('valid_fit')
        m.outputs.append(m.outputs[0]+'_wr_en')
        for i in m.inputs:
            if 'From' in i:
                m.start = i.replace(m.name,'')+'start'
        m.done = m.name+'_start'
        seen_done10_0 = True

    ####################################################
    if('mod' not in sys.argv): # If you want processing modules in the print out
        string_processing += '\n'
        string_processing += '\n' +  m.module + ' ' +m.parameters + ' ' +m.name + '('
        k = 1
        for n,i in zip(m.in_names,m.inputs): # Loop over inputs and input names 
            if m.module != 'LayerRouter' and m.module != 'DiskRouter': # Special cases for signals without normal read_add
                if n == 'tpar1in':
                    string_processing += '\n' +  '.read_add_pars1('+i+'_read_add),'
                elif n == 'tpar2in':
                    string_processing += '\n' +  '.read_add_pars2('+i+'_read_add),'
                elif n == 'tpar3in':
                    string_processing += '\n' +  '.read_add_pars3('+i+'_read_add),'
                elif n == 'incomming_proj_data_stream':
                    string_processing += '\n' +  '.valid_incomming_proj_data_stream('+i+'_en),'
                elif n == 'incomming_match_data_stream':
                    string_processing += '\n' +  '.valid_incomming_match_data_stream('+i+'_en),'
                elif 'fullmatch' in n:
                    string_processing += '\n' +  '.number'+n.split('match')[-1]+'('+i+'_number),'
                    string_processing += '\n' +  '.read_add'+n.split('match')[-1]+'('+i+'_read_add),'
                    string_processing += '\n' +  '.read_en'+n.split('match')[-1]+'('+i+'_read_en),'
                elif 'allstubin' in n:
                    string_processing += '\n' +  '.read_add_'+n+'('+i+'_read_add),'
                elif 'allprojin' in n:
                    string_processing += '\n' +  '.read_add_'+n+'('+i+'_read_add),'
                else:
                    string_processing += '\n' +  '.number_in_'+n+'('+i+'_number),'
                    string_processing += '\n' +  '.read_add_'+n+'('+i+'_read_add),'
            string_processing += '\n' +  '.'+n+'('+i+'),' # Write the signal name
            k = k + 1
        for n,o in zip(m.out_names,m.outputs): # Loop over outputs and output names 
            string_processing += '\n' +  '.'+n+'('+o+'),'
        string_processing += '\n' +  '.start('+m.start+'),'
        string_processing += '\n' +  '.done('+m.done+'),'
        string_processing += '\n' +  m.common
        string_processing += '\n' +  ');'

# Write the final lines

for ep in epilogue:
    string_epilogue += '\n' +  ep.strip()
    
starts = [x.split('),')[0] for x in (string_memories+string_processing).split('.start(')]

for x in set(starts[1:]):
    if len(x)>1 and 'IL' not in x:
        string_starts += '\n' +  'wire [1:0] '+ x +';'

if region == 'D3':
    print 'Processing D3'
    print 'Memories implemented=',len(memories)
    print 'Processing modules implemented=',len(modules)
    string_prologue = string_prologue.replace('Tracklet_processing','Tracklet_processingD3')
if region == 'D5':
    print 'Processing D5'
    print 'Memories implemented=',len(memories)
    print 'Processing modules implemented=',len(modules)
    string_prologue = string_prologue.replace('Tracklet_processing','Tracklet_processingD5')
if region == 'D3D4':
    print 'Processing D3D4'
    print 'Memories implemented =',len(memories)
    print 'Processing modules implemented =',len(modules)
    string_prologue = string_prologue.replace('module Tracklet_processing','module Tracklet_processingD3D4')
    
g = open('test.txt','w')
g.write(string_prologue)
g.write(string_starts)
g.write(string_memories)
g.write(string_processing)
g.write(string_epilogue)
