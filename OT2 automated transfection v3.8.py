# resource on the tech specs of Opentrons pipettes: https://cleanup-kit.sandbox.opentrons.com/pipettes/

# imports
from opentrons import protocol_api
import csv

# metadata
metadata = {
    "protocolName": " 20241105_updated uORF library_v3.6 Protocol_v3.7",
    "author": "Evan Holbrook <evanholb@mit.edu>",
    "description": "Automates all steps in the 3-step transfection protocol: i) mix DNA; ii) prepare P3000/L3000; iii) transfect cells. Designed for use with up to 3 OT-2 tube racks (72 tube max)."
}

# requirements
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

# for the OT-2 speaker
import subprocess 
from opentrons import types
AUDIO_FILE_PATH = '/etc/audio/speaker-test.mp3' 
def run_quiet_process(command): 
    subprocess.check_output('{} &> /dev/null'.format(command), shell=True) 
def test_speaker(): 
    print('Speaker') 
    print('Next\t--> CTRL-C')
    try:
        run_quiet_process('mpg123 {}'.format(AUDIO_FILE_PATH))
    except KeyboardInterrupt:
        pass
        print()

# transfection parameters - customize to your liking
OM = 0.05 # uL of Opti-MEM per ng of DNA
P3K = 0.0022 # uL of P3000 per ng of DNA
L3K = 0.0022 # uL of L3000 per ng of DNA
Excess = 1.2 # excess multiplier for pipetting error

# csv import example to specify DNA details - modify by pasting in your csv from this template, WHILE KEEPING the header names below: https://docs.google.com/spreadsheets/d/1kNe_YEnk-sQBAQ1Gp-82OicvIDbjyB7sQ7VMvBwP4zU/edit?usp=sharing
csv_raw = '''DNA source,DNA destination,L3K/OM MM destination,Plate destination,Transfection type,Contents,Concentration (ng/uL),DNA wanted (ng)
A1.1,D6.1,D6.2,A1.1,Single,mNG,75,500

A2.1,A1.2,A1.3,A2.1,Single,mKO2,50,500

A1.1,A2.2,A2.3,A3.1,Co,mNG,75,250

A2.1,A2.2,A2.3,A3.1,Co,mKO2,50,250

A3.1,A3.2,A3.3,A4.1,Single,Transfection ctrl,500,500

A4.1,A4.2,A4.3,A5.1,Single,pEH004 (u18),141,500

A5.1,A5.2,A5.3,A6.1,Single,pGW0127 (uORF),248.1,500

A6.1,A6.2,A6.3,B1.1,Single,pEH023 (u31),155.1,500

B1.1,B1.2,B1.3,B2.1,Single,pEH030 (u38),183,500

B2.1,B2.2,B2.3,B3.1,Single,pEH028 (u36),154.5,500

B3.1,B3.2,B3.3,B4.1,Single,pEH025 (u33),309.6,500

B4.1,B4.2,B4.3,B5.1,Single,pEH024 (u32),173.3,500

B5.1,B5.2,B5.3,B6.1,Single,pEH027 (u35),176.8,500

B6.1,B6.2,B6.3,C1.1,Single,pEH016 (u30),281.7,500

C1.1,C1.2,C1.3,C2.1,Single,pGW0132 (u4),157.8,500

C2.1,C2.2,C2.3,C3.1,Single,pGW0129 (u1),296,500

C3.1,C3.2,C3.3,C4.1,Single,pGW0138 (u10),328,500

C4.1,C4.2,C4.3,C5.1,Single,pGW0140 (u12),322,500

C5.1,C5.2,C5.3,C6.1,Single,pGW0139 (u11),296,500

C6.1,C6.2,C6.3,D1.1,Single,pGW0133 (u5),298,500

D1.1,D1.2,D2.3,D2.1,Single,pGW0128 (wuORF),168,500

D2.1,D2.2,D3.3,D3.1,Single,pGW0141 (u13),203,500

D3.1,D3.2,D4.3,D4.1,Single,pGW0142 (u14),244.6,500

D4.1,D4.2,D5.3,D5.1,Single,pEH029 (u37),346.7,500

D5.1,D5.2,D6.3,D6.1,Single,pGW0151 (inert),247.2,500'''

csv_data = csv_raw.splitlines()
csv_reader = csv.DictReader(csv_data)

# initialize lists - csv_reader is a dictionary, so I'm using lists here because I need indexing power
DNA_sources_, DNA_dests_, L3K_dests_, plate_dests,transfection_types,transfection_types_, tube_names, uL_DNA_, uL_OM_, uL_P3K_, uL_L3K_ = [],[],[],[],[],[],[],[],[],[],[]

for a in csv_reader:
    # convert parts of csv_reader, which is a dictionary, to a list which has indices
    DNA_sources_.append(a['DNA source'])
    DNA_dests_.append(a['DNA destination'])
    L3K_dests_.append(a['L3K/OM MM destination'])
    plate_dests.append(a['Plate destination'])
    transfection_types_.append(a['Transfection type'])
    tube_names.append(a['Contents'])
    
    # run transfection calculations and store them in a list
    uL_DNA_.append( (float(a['DNA wanted (ng)']) / float(a['Concentration (ng/uL)'])) * Excess)
    uL_OM_.append(float(a['DNA wanted (ng)']) * OM * Excess)
    uL_P3K_.append(float(a['DNA wanted (ng)']) * P3K * Excess)
    uL_L3K_.append(float(a['DNA wanted (ng)']) * L3K * Excess)

# generate abbreviated lists, which combine technical replicates into 1 master mix
DNA_sources, DNA_dests, L3K_dests, uL_DNA, uL_OM, uL_P3K, uL_L3K, skips = [],[],[],[],[],[],[],[]
for a in range(len(DNA_sources_)):    
    if a in skips:
        continue
    
    else:
        skips.append(a)
        reps = [a]
        for b in range(a+1, len(DNA_sources_)):
            if DNA_sources_[a] == DNA_sources_[b] and DNA_dests_[a] == DNA_dests_[b]:
                skips.append(b)
                reps.append(b)

        DNA_volume = 0
        OM_volume = 0
        P3K_volume = 0
        L3K_volume = 0
        for c in reps:
            DNA_volume += uL_DNA_[c]
            OM_volume += uL_OM_[c]
            P3K_volume += uL_P3K_[c]
            L3K_volume += uL_L3K_[c]

        DNA_sources.append(DNA_sources_[a])
        DNA_dests.append(DNA_dests_[a])
        L3K_dests.append(L3K_dests_[a])
        transfection_types.append(transfection_types_[a])
        
        uL_DNA.append(DNA_volume)
        uL_OM.append(OM_volume)
        uL_P3K.append(P3K_volume)
        uL_L3K.append(L3K_volume)

# raise SystemExit if any DNA volumes are too small (< 1 uL)
for a in range(len(uL_DNA)):
    if uL_DNA[a] < 1:
        print('DNA concentration in tube', tube_names[a], 'is too high (volume required is below the minimum of 1 uL). Please dilute DNA so at least 1 uL can be used.')
        raise SystemExit('Program halted. See above for details.')

# generate list of wells in a 24-well plate for later
rows = ['A','B','C','D']
columns = [1,2,3,4,5,6]
wells = []
for a in rows:
    for b in columns:
        wells.append(a+str(b))

# protocol run function
def run(protocol: protocol_api.ProtocolContext):
    # load labware
    tuberack1 = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap", location="4"
    )

    tuberack2 = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap", location="5"
    )

    tuberack3 = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap", location="6"
    )

    plate1 = protocol.load_labware(
        "corning_24_wellplate_3.4ml_flat", location="2"
    )

    plate2 = protocol.load_labware(
        "corning_24_wellplate_3.4ml_flat", location="3"
    )
    
    tiprack1 = protocol.load_labware(
        "opentrons_96_tiprack_300ul", location="9"
    )
    
    tiprack2 = protocol.load_labware(
        "opentrons_96_tiprack_20ul", location="8"
    )

    # load pipettes
    right_pipette = protocol.load_instrument(
        "p300_single_gen2", mount="right", tip_racks=[tiprack1]
    )
    left_pipette = protocol.load_instrument(
        "p20_single_gen2", mount="left", tip_racks=[tiprack2]
    )

    # specify custom pipette parameters
    right_pipette.flow_rate.aspirate = 250 #in uL/sec
    right_pipette.flow_rate.dispense = 250 #in uL/sec
    left_pipette.flow_rate.aspirate = 20 #in uL/sec
    left_pipette.flow_rate.dispense = 20 #in uL/sec
        
    right_pipette.well_bottom_clearance.aspirate = 0.1 #clearance in mm from bottom of tube when aspirating
    right_pipette.well_bottom_clearance.dispense = 0.5 #clearance in mm from bottom of tube when dispensing
    left_pipette.well_bottom_clearance.aspirate = 0.1 #clearance in mm from bottom of tube when aspirating
    left_pipette.well_bottom_clearance.dispense = 0.5 #clearance in mm from bottom of tube when dispensing

    # below are commands:
    
    # Step 1) transfer DNA from source tubes to destination tubes
    count = 0
    for a in range(len(uL_DNA)):
        source_well = DNA_sources[a].split('.')[0]
        destination_well = DNA_dests[a].split('.')[0]
        source_rack = DNA_sources[a].split('.')[-1]
        dest_rack = DNA_dests[a].split('.')[-1]
        DNA_vol = uL_DNA[a]

        if source_rack == '1':
            source = tuberack1[source_well]
        elif source_rack == '2':
            source = tuberack2[source_well]
        elif source_rack == '3':
            source = tuberack3[source_well]

        if dest_rack == '1':
            dest = tuberack1[destination_well]
        elif dest_rack == '2':
            dest = tuberack2[destination_well]
        elif dest_rack == '3':
            dest = tuberack3[destination_well]


        # mix DNA for tubes that have cotransfections
        try:
            trans_type = transfection_types[count]
        except:
            trans_type = 'blah'

        # if/else to deal with co-transfections
        try:
            if trans_type == 'Co' and DNA_dests[count+1] != DNA_dests[count]:            
                mix_param = (3,20)
                   
            else:
                mix_param = (0,0)

        except:
            if trans_type == 'Co' and count == len(DNA_dests)-1:
                mix_param = (3,20)

            else:
                mix_param = (0,0)

        # figure out whether a DNA source tube needs to be mixed or not
        past_tubes = DNA_sources[0:a]
        if DNA_sources[a] in past_tubes:
            mix_param_before = (0,0)
        elif DNA_sources[a] not in past_tubes:
            mix_param_before = (3,20)
            
        count += 1

        # if/else for choosing the appropriate pipette to use
        if DNA_vol >= 20:
            right_pipette.transfer(
                volume = DNA_vol,
                source = source,
                dest = dest,
                mix_before = mix_param_before, # mixes source well before aspiration 3 times with 20 uL volume
                mix_after = mix_param,
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'always'
                ) 

        else:
            left_pipette.transfer(
                volume = DNA_vol,
                source = source,
                dest = dest,
                mix_before = mix_param_before, # mixes source well before aspiration 3 times with 20 uL volume
                mix_after = mix_param,
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'always'
                )    

    # pause robot to allow time to get OM and P3K
    #test_speaker() ##############################################################################################################################################################


    right_pipette.well_bottom_clearance.aspirate = 0.5 #clearance in mm from bottom of tube when aspirating
    right_pipette.well_bottom_clearance.dispense = 0.5 #clearance in mm from bottom of tube when dispensing
    left_pipette.well_bottom_clearance.aspirate = 0.5 #clearance in mm from bottom of tube when aspirating
    left_pipette.well_bottom_clearance.dispense = 0.5 #clearance in mm from bottom of tube when dispensing
    
    protocol.pause('Now, get your OM and P3000 and place in tuberack at the  locations specified on the spreadsheet')

    # Step 2) Adding OM/P3000 master mix to DNA tubes, mixing with OM/L3000

    # figure out total reagent volumes needed
    OM_MM_vol = sum(uL_OM)*1.2
    P3K_MM_vol = sum(uL_P3K)*1.2
    L3K_MM_vol = sum(uL_L3K)*1.2

    # prepare OM/P3K MM

    # P3000 reagent pipetting
    if P3K_MM_vol >= 20:
        right_pipette.transfer(
            volume = P3K_MM_vol,
            source = tuberack3['D4'],
            dest = tuberack3['D2'],
            blow_out = True,
            blowout_location = 'destination well',
            new_tip = 'always'
            )
        
    else:
        left_pipette.transfer(
            volume = P3K_MM_vol,
            source = tuberack3['D4'],
            dest = tuberack3['D2'],
            blow_out = True,
            blowout_location = 'destination well',
            new_tip = 'always'
            )

    # Opti-MEM reagent pipetting
    if OM_MM_vol > 20 and OM_MM_vol <= 200:
        right_pipette.transfer(
            volume = OM_MM_vol,
            source = tuberack3['D6'],
            dest = tuberack3['D2'],
            mix_after = (3,OM_MM_vol),
            blow_out = True,
            blowout_location = 'destination well',
            new_tip = 'always'
            )

    if OM_MM_vol > 200:
        right_pipette.transfer(
            volume = OM_MM_vol,
            source = tuberack3['D6'],
            dest = tuberack3['D2'],
            mix_after = (3,200),
            blow_out = True,
            blowout_location = 'destination well',
            new_tip = 'always'
            )
        
    elif OM_MM_vol <= 20:
        left_pipette.transfer(
            volume = OM_MM_vol,
            source = tuberack3['D6'],
            dest = tuberack3['D2'],
            mix_after = (3,OM_MM_vol),
            blow_out = True,
            blowout_location = 'destination well',
            new_tip = 'always'
            )

    # distribute OM/P3K MM to DNA dest tubes, which have DNA in them
    count = 0
    while count < len(DNA_dests):
        destination_well = DNA_dests[count].split('.')[0]
        dest_rack = DNA_dests[count].split('.')[-1]

        try:
            trans_type = transfection_types[count]
        except:
            trans_type = 'blah'
        
        # if/else to deal with co-transfections
        if trans_type == 'Co':            
            # gather all tubes that should be cotransfected together by appending their indicies; searching for tubes with the same 'DNA_dest' location
            cotrans_group_indices = [count]
            for b in range(count+1,len(DNA_dests)):
                if (DNA_dests[count] == DNA_dests[b]) and (L3K_dests[count] == L3K_dests[b]):
                    cotrans_group_indices.append(b)

            OM_P3K_MM_vol = 0            
            for c in cotrans_group_indices:
                OM_P3K_MM_vol += (uL_OM[c]+uL_P3K[c])
            
            count += len(cotrans_group_indices)        

        else:
            OM_P3K_MM_vol = uL_OM[count]+uL_P3K[count]
            
            count += 1

        if dest_rack == '1':
            dest = tuberack1[destination_well]
        elif dest_rack == '2':
            dest = tuberack2[destination_well]
        elif dest_rack == '3':
            dest = tuberack3[destination_well]

        if OM_P3K_MM_vol > 20 and OM_P3K_MM_vol <= 200:
            right_pipette.transfer(
                volume = OM_P3K_MM_vol,
                source = tuberack3['D2'],
                dest = dest,
                mix_after = (3, OM_P3K_MM_vol),
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'always'
                )

        elif OM_P3K_MM_vol > 200:
            right_pipette.transfer(
                volume = OM_P3K_MM_vol,
                source = tuberack3['D2'],
                dest = dest,
                mix_after = (3, 200),
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'always'
                )
            
        else:
            left_pipette.transfer(
                volume = OM_P3K_MM_vol,
                source = tuberack3['D2'],
                dest = dest,
                mix_after = (3, 15),
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'always'
                )
    
    # prepare OM/L3K MM
    # pause robot to allow time to get L3K
    #test_speaker() ##############################################################################################################################################################
    protocol.pause('Now, get your L3000 and place in tuberack at the location specified on the spreadsheet')
    
    # L3000 reagent pipetting
    if L3K_MM_vol >= 20:
        right_pipette.transfer(
            volume = L3K_MM_vol,
            source = tuberack3['D3'],
            dest = tuberack3['D1'],
            blow_out = True,
            blowout_location = 'destination well',
            new_tip = 'always'
            )
        
    else:
        left_pipette.transfer(
            volume = L3K_MM_vol,
            source = tuberack3['D3'],
            dest = tuberack3['D1'],
            blow_out = True,
            blowout_location = 'destination well',
            new_tip = 'always'
            )
        
    # Opti-MEM pipetting    
    if OM_MM_vol <= 750:
        if OM_MM_vol > 20 and OM_MM_vol <= 200:
            right_pipette.transfer(
                volume = OM_MM_vol,
                source = tuberack3['D6'],
                dest = tuberack3['D1'],
                mix_after = (3,OM_MM_vol),
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'always'
                )

        elif OM_MM_vol > 200:
            right_pipette.transfer(
                volume = OM_MM_vol,
                source = tuberack3['D6'],
                dest = tuberack3['D1'],
                mix_after = (3,200),
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'always'
                )
            
        elif OM_MM_vol <= 20:
            left_pipette.transfer(
                volume = OM_MM_vol,
                source = tuberack3['D6'],
                dest = tuberack3['D1'],
                mix_after = (3,OM_MM_vol),
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'always'
                )
            
    elif OM_MM_vol > 750:
        right_pipette.transfer(
            volume = OM_MM_vol,
            source = tuberack3['D5'],
            dest = tuberack3['D6'],
            blow_out = True,
            blowout_location = 'destination well',
            new_tip = 'always'
            )
              
        if OM_MM_vol > 20 and OM_MM_vol <= 200:
            right_pipette.transfer(
                volume = OM_MM_vol,
                source = tuberack3['D6'],
                dest = tuberack3['D1'],
                mix_after = (3,OM_MM_vol),
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'always'
                )

        elif OM_MM_vol > 200:
            right_pipette.transfer(
                volume = OM_MM_vol,
                source = tuberack3['D6'],
                dest = tuberack3['D1'],
                mix_after = (3,200),
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'always'
                )
            
        elif OM_MM_vol <= 20:
            left_pipette.transfer(
                volume = OM_MM_vol,
                source = tuberack3['D6'],
                dest = tuberack3['D1'],
                mix_after = (3,OM_MM_vol),
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'always'
                )     

    # distribute OM/L3K MM to empty tubes
    right_pipette.pick_up_tip()
    left_pipette.pick_up_tip()
    
    count = 0
    while count < len(L3K_dests):
        destination_well = L3K_dests[count].split('.')[0]
        dest_rack = L3K_dests[count].split('.')[-1]

        try:
            trans_type = transfection_types[count]
        except:
            trans_type = 'blah'
        
        # if/else to deal with co-transfections
        if trans_type == 'Co':            
            # gather all tubes that should be cotransfected together by appending their indicies; searching for tubes with the same 'DNA_dest' location
            cotrans_group_indices = [count]
            for b in range(count+1,len(DNA_dests)):
                if (DNA_dests[count] == DNA_dests[b]) and (L3K_dests[count] == L3K_dests[b]):
                    cotrans_group_indices.append(b)

            OM_L3K_MM_vol = 0            
            for c in cotrans_group_indices:
                OM_L3K_MM_vol += (uL_OM[c]+uL_L3K[c])
            
            count += len(cotrans_group_indices)        

        else:
            OM_L3K_MM_vol = uL_OM[count]+uL_L3K[count]
            
            count += 1
    
        if dest_rack == '1':
            dest = tuberack1[destination_well]
        elif dest_rack == '2':
            dest = tuberack2[destination_well]
        elif dest_rack == '3':
            dest = tuberack3[destination_well]

        if OM_L3K_MM_vol > 20:
            right_pipette.transfer(
                volume = OM_L3K_MM_vol,
                source = tuberack3['D1'],
                dest = dest,
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'never'
                )
        else:
            left_pipette.transfer(
                volume = OM_L3K_MM_vol,
                source = tuberack3['D1'],
                dest = dest,
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'never'
                )   

    right_pipette.drop_tip()
    left_pipette.drop_tip()    

    # pipette OM/P3K/DNA mixture into OM/L3K mixture

    count = 0
    while count < len(L3K_dests):
        source_well = DNA_dests[count].split('.')[0]
        destination_well = L3K_dests[count].split('.')[0]
        source_rack = DNA_dests[count].split('.')[-1]
        dest_rack = L3K_dests[count].split('.')[-1]

        try:
            trans_type = transfection_types[count]
        except:
            trans_type = 'blah'
        
        # if/else to deal with co-transfections
        if trans_type == 'Co':            
            # gather all tubes that should be cotransfected together by appending their indicies; searching for tubes with the same 'DNA_dest' location
            cotrans_group_indices = [count]
            for b in range(count+1,len(DNA_dests)):
                if (DNA_dests[count] == DNA_dests[b]) and (L3K_dests[count] == L3K_dests[b]):
                    cotrans_group_indices.append(b)

            mixing_vol = 0            
            for c in cotrans_group_indices:
                mixing_vol += (uL_DNA[c]+uL_OM[c]+uL_P3K[c])
            
            count += len(cotrans_group_indices)        

        else:
            mixing_vol = (uL_DNA[count]+uL_OM[count]+uL_P3K[count])
            
            count += 1

        if source_rack == '1':
            source = tuberack1[source_well]
        elif source_rack == '2':
            source = tuberack2[source_well]
        elif source_rack == '3':
            source = tuberack3[source_well]

        if dest_rack == '1':
            dest = tuberack1[destination_well]
        elif dest_rack == '2':
            dest = tuberack2[destination_well]
        elif dest_rack == '3':
            dest = tuberack3[destination_well]

            
        if mixing_vol > 20 and mixing_vol <= 200:
            right_pipette.transfer(
                volume = mixing_vol,
                source = source,
                dest = dest,
                mix_after = (3,mixing_vol),
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'always'
                )

        elif mixing_vol > 200:
            right_pipette.transfer(
                volume = mixing_vol,
                source = source,
                dest = dest,
                mix_after = (3,200),
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'always'
                )
            
        else:
            left_pipette.transfer(
                volume = mixing_vol,
                source = source,
                dest = dest,
                mix_after = (3,20),
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'always'
                )

    # pause robot to allow time to get cells and incubate transfection mixes
    #test_speaker() ##############################################################################################################################################################
    protocol.pause('Now, incubate the mixture for 10 mins and get your cells and place in the deck specified in the OT-2 protocol')

    # Step 3) Adding transfection mixes to cells


    # specify custom pipette parameters
    right_pipette.flow_rate.dispense = 50 #in uL/sec; slower to not disturb monolayer
    right_pipette.well_bottom_clearance.dispense = 2 #clearance in mm from bottom of tube when dispensing
    left_pipette.well_bottom_clearance.dispense = 2 #clearance in mm from bottom of tube when dispensing
    
    count = 0
    while count < len(plate_dests):

        source_well = L3K_dests_[count].split('.')[0]
        destination_well = plate_dests[count].split('.')[0]
        source_rack = L3K_dests_[count].split('.')[-1]
        dest_rack = plate_dests[count].split('.')[-1]
        
        try:
            trans_type = transfection_types_[count]
        except:
            trans_type = 'blah'
        
        # if/else to deal with co-transfections
        if trans_type == 'Co':            
            # gather all tubes that should be cotransfected together by appending their indicies; searching for tubes with the same 'DNA_dest' location
            cotrans_group_indices = [count]
            for b in range(count+1,len(DNA_dests_)):
                if (DNA_dests_[count] == DNA_dests_[b]) and (plate_dests[count] == plate_dests[b]):
                    cotrans_group_indices.append(b)

            transfection_vol = 0            
            for c in cotrans_group_indices:
                transfection_vol += (uL_DNA_[c]+uL_OM_[c]*2+uL_P3K_[c]*2)/Excess
            
            count += len(cotrans_group_indices)        

        else:
            transfection_vol = (uL_DNA_[count]+uL_OM_[count]*2+uL_P3K_[count]*2)/Excess
            
            count += 1

        if source_rack == '1':
            source = tuberack1[source_well]
        elif source_rack == '2':
            source = tuberack2[source_well]
        elif source_rack == '3':
            source = tuberack3[source_well]

        if dest_rack == '1':
            dest = plate1[destination_well]
        elif dest_rack == '2':
            dest = plate2[destination_well]


        if transfection_vol >= 20:
            right_pipette.transfer(
                volume = transfection_vol,
                source = source,
                dest = dest,
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'always'
                )
            
        else:
            left_pipette.transfer(
                volume = transfection_vol,
                source = source,
                dest = dest,
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'always'
                )
            
    #test_speaker() ##############################################################################################################################################################

        
