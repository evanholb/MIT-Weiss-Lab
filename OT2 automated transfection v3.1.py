# resource on the tech specs of Opentrons pipettes: https://cleanup-kit.sandbox.opentrons.com/pipettes/

# imports
from opentrons import protocol_api
import csv

# metadata
metadata = {
    "protocolName": "Transfection: Complete Protocol_v3",
    "author": "Evan Holbrook <evanholb@mit.edu>",
    "description": "Automates all steps in the 3-step transfection protocol: i) mix DNA; ii) prepare P3000/L3000; iii) transfect cells. Designed for use with up to 3 OT-2 tube racks (72 tube max)."
}

# requirements
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

# transfection parameters - customize to your liking
OM = 0.05 # uL of Opti-MEM per ng of DNA
P3K = 0.0022 # uL of P3000 per ng of DNA
L3K = 0.0022 # uL of L3000 per ng of DNA
Excess = 1.2 # excess multiplier for pipetting error

# csv import example to specify DNA details - modify by pasting in your csv from this template, WHILE KEEPING the header names below: https://docs.google.com/spreadsheets/d/1kNe_YEnk-sQBAQ1Gp-82OicvIDbjyB7sQ7VMvBwP4zU/edit?usp=sharing
csv_raw = '''DNA source,DNA destination,L3K/OM MM destination,Plate destination,Transfection type,Contents,Concentration (ng/uL),DNA wanted (ng)
A1.1,B5.1,D3.1,A1.1,Single,eYFPG5A,85.1,300
A2.1,B6.1,D4.1,A2.1,Single,mKO2,100,300
A3.1,C1.1,D5.1,A3.1,Single,tagBFP,161.8,300
A1.1,C2.1,D6.1,A4.1,Co,eYFPG5A,85.1,166.6666667
A2.1,C2.1,D6.1,A4.1,Co,mKO2,100,166.6666667
A3.1,C2.1,D6.1,A4.1,Co,tagBFP,161.8,166.6666667
A4.1,C3.1,A1.2,A6.1,Co,0u+ to 1u- : epegRNA,56.4,100
A5.1,C3.1,A1.2,A6.1,Co,0u+ to 1u- : PEmax,255.8,300
A6.1,C3.1,A1.2,A6.1,Co,0u+ to 1u- : 2ndary cut,101,100
A2.1,C3.1,A1.2,A6.1,Co,0u+ to 1u- : mKO2,100,100
B1.1,C4.1,A2.2,A6.1,Poly,0u+ (pGW0077),121.6,200
B4.1,C5.1,A3.2,B1.1,Co,0u+ to 1u- : NO epegRNA,100,100
A5.1,C5.1,A3.2,B1.1,Co,0u+ to 1u- : PEmax,255.8,300
A6.1,C5.1,A3.2,B1.1,Co,0u+ to 1u- : 2ndary cut,101,100
A2.1,C5.1,A3.2,B1.1,Co,0u+ to 1u- : mKO2,100,100
B1.1,C4.1,A2.2,B1.1,Poly,0u+ (pGW0077),121.6,200
A4.1,C3.1,A1.2,B2.1,Co,0u+ to 1u- : epegRNA,56.4,100
A5.1,C3.1,A1.2,B2.1,Co,0u+ to 1u- : PEmax,255.8,300
A6.1,C3.1,A1.2,B2.1,Co,0u+ to 1u- : 2ndary cut,101,100
A2.1,C3.1,A1.2,B2.1,Co,0u+ to 1u- : mKO2,100,100
B2.1,C6.1,A4.2,B3.1,Single,pEH017,37,250
B2.1,D1.1,A5.2,B4.1,Co,pEH017,37,250
B3.1,D1.1,A5.2,B4.1,Co,pYW35,164.6,250
B4.1,D2.1,A6.2,A5.1,Single,Transfection ctrl,500,500'''

csv_data = csv_raw.splitlines()
csv_reader = csv.DictReader(csv_data)

# initialize lists - csv_reader is a dictionary, so I'm using lists here because I need indexing power
DNA_sources, DNA_dests, L3K_dests, plate_dests,transfection_types, tube_names, uL_DNA, uL_OM, uL_P3K, uL_L3K = [],[],[],[],[],[],[],[],[],[]

for a in csv_reader:
    # convert parts of csv_reader, which is a dictionary, to a list which has indices
    DNA_sources.append(a['DNA source'])
    DNA_dests.append(a['DNA destination'])
    L3K_dests.append(a['L3K/OM MM destination'])
    plate_dests.append(a['Plate destination'])
    transfection_types.append(a['Transfection type'])
    tube_names.append(a['Contents'])
    
    # run transfection calculations and store them in a list
    uL_DNA.append( (float(a['DNA wanted (ng)']) / float(a['Concentration (ng/uL)'])) * Excess)
    uL_OM.append(float(a['DNA wanted (ng)']) * OM * Excess)
    uL_P3K.append(float(a['DNA wanted (ng)']) * P3K * Excess)
    uL_L3K.append(float(a['DNA wanted (ng)']) * L3K * Excess)

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
        
    right_pipette.well_bottom_clearance.aspirate = 0.5 #clearance in mm from bottom of tube when aspirating
    right_pipette.well_bottom_clearance.dispense = 0.5 #clearance in mm from bottom of tube when dispensing
    left_pipette.well_bottom_clearance.aspirate = 0.5 #clearance in mm from bottom of tube when aspirating
    left_pipette.well_bottom_clearance.dispense = 0.5 #clearance in mm from bottom of tube when dispensing

    # below are commands:
    
    # Step 1) transfer DNA from source tubes to destination tubes
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

        # if/else for choosing the appropriate pipette to use
        if DNA_vol >= 20:
            right_pipette.transfer(
                volume = DNA_vol,
                source = source,
                dest = dest,
                mix_before = (3, 25), # mixes source well before aspiration 3 times with 25 uL volume
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'always'
                ) 

        else:
            left_pipette.transfer(
                volume = DNA_vol,
                source = source,
                dest = dest,
                mix_before = (3, 15), # mixes source well before aspiration 3 times with 25 uL volume
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'always'
                )

    # pause robot to allow time to get OM, P3K, and L3K
    protocol.pause('Now, get your OM, P3000, and L3000 and place in tuberack at the  locations specified on the spreadsheet')

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
    if OM_MM_vol > 20:
        right_pipette.transfer(
            volume = OM_MM_vol,
            source = tuberack3['D6'], ######## NEED TO EDIT TO ALLOW MULTIPLE OM TUBES
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
    for a in range(len(DNA_dests)): 
        OM_P3K_MM_vol = uL_OM[a]+uL_P3K[a]
        source_well = 'D2'
        destination_well = DNA_dests[a].split('.')[0] ###########################
        dest_rack = DNA_dests[a].split('.')[-1]

        if dest_rack == '1':
            dest = tuberack1[destination_well]
        elif dest_rack == '2':
            dest = tuberack2[destination_well]
        elif dest_rack == '3':
            dest = tuberack3[destination_well]

        if OM_P3K_MM_vol >= 20:
            right_pipette.transfer(
                volume = OM_P3K_MM_vol,
                source = tuberack3[source_well],
                dest = dest,
                mix_after = (3, OM_P3K_MM_vol),
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'always'
                )
        else:
            left_pipette.transfer(
                volume = OM_P3K_MM_vol,
                source = tuberack3[source_well],
                dest = dest,
                mix_after = (3, 15),
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'always'
                )
    
    # prepare OM/L3K MM

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
    if OM_MM_vol > 20:
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
    
    for a in range(len(L3K_dests)): 
        OM_L3K_MM_vol = uL_OM[a]+uL_L3K[a]
        source_well = 'D1'
        destination_well = L3K_dests[a].split('.')[0]
        dest_rack = L3K_dests[a].split('.')[-1]

        if dest_rack == '1':
            dest = tuberack1[destination_well]
        elif dest_rack == '2':
            dest = tuberack2[destination_well]
        elif dest_rack == '3':
            dest = tuberack3[destination_well]

        if OM_L3K_MM_vol >= 20:
            right_pipette.transfer(
                volume = OM_L3K_MM_vol,
                source = tuberack3[source_well],
                dest = dest,
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'never'
                )
        else:
            left_pipette.transfer(
                volume = OM_L3K_MM_vol,
                source = tuberack3[source_well],
                dest = dest,
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'never'
                )   

    right_pipette.drop_tip()
    left_pipette.drop_tip()    

    # pipette OM/P3K/DNA mixture into OM/L3K mixture
    for a in range(len(L3K_dests)):
        OM_P3K_DNA_MM_vol = uL_DNA[a]+uL_OM[a]+uL_P3K[a]
        source_well = DNA_dests[a].split('.')[0]
        destination_well = L3K_dests[a].split('.')[0]
        source_rack = DNA_dests[a].split('.')[-1]
        dest_rack = L3K_dests[a].split('.')[-1]

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

            
        if OM_P3K_DNA_MM_vol >= 20:
            right_pipette.transfer(
                volume = OM_P3K_DNA_MM_vol,
                source = source,
                dest = dest,
                mix_after = (3,OM_P3K_DNA_MM_vol),
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'always'
                )
            
        else:
            left_pipette.transfer(
                volume = OM_P3K_DNA_MM_vol,
                source = source,
                dest = dest,
                mix_after = (3,20),
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'always'
                )

    # pause robot to allow time to get cells and incubate transfection mixes
    protocol.pause('Now, incubate the mixture for 10 mins and get your cells and place in the deck specified in the OT-2 protocol')

    # Step 3) Adding transfection mixes to cells

    right_pipette.well_bottom_clearance.dispense = 2 #clearance in mm from bottom of tube when dispensing
    left_pipette.well_bottom_clearance.dispense = 2 #clearance in mm from bottom of tube when dispensing
    
    count = 0
    while count < len(plate_dests):

        source_well = L3K_dests[count].split('.')[0]
        destination_well = plate_dests[count].split('.')[0]
        source_rack = L3K_dests[count].split('.')[-1]
        dest_rack = plate_dests[count].split('.')[-1]
        
        try:
            trans_type = transfection_types[count]
        except:
            trans_type = 'blah'
        
        # if/else to deal with co-transfections
        if trans_type == 'Co':            
            # gather all tubes that should be cotransfected together by appending their indicies; searching for tubes with the same 'DNA_dest' location
            cotrans_group_indices = [count]
            for b in range(count+1,len(DNA_dests)):
                if (DNA_dests[count].split('.')[0] == DNA_dests[b].split('.')[0]) and (plate_dests[count].split('.')[0] == plate_dests[b].split('.')[0]):
                    cotrans_group_indices.append(b)

            transfection_vol = 0            
            for c in cotrans_group_indices:
                transfection_vol += (uL_DNA[c]+uL_OM[c]*2+uL_P3K[c]*2)/Excess
            
            count += len(cotrans_group_indices)        

        else:
            transfection_vol = (uL_DNA[count]+uL_OM[count]*2+uL_P3K[count]*2)/Excess
            
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
        
