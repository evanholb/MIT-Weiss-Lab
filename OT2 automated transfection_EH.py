# resource on the tech specs of Opentrons pipettes: https://cleanup-kit.sandbox.opentrons.com/pipettes/

# imports
from opentrons import protocol_api
import csv

# metadata
metadata = {
    "protocolName": "Transfection: Complete Protocol",
    "author": "Evan Holbrook <evanholb@mit.edu>",
    "description": "Automates all steps in the 3-step transfection protocol: i) mix DNA; ii) prepare P3000/L3000; iii) transfect cells. Designed for use with a single OT-2 tube rack (24 tube max)."
}

# requirements
requirements = {"robotType": "OT-2", "apiLevel": "2.19"}

# transfection parameters - customize to your liking
OM = 0.05 # uL of Opti-MEM per ng of DNA
P3K = 0.0022 # uL of P3000 per ng of DNA
L3K = 0.0022 # uL of L3000 per ng of DNA
Excess = 1.2 # excess multiplier for pipetting error

# csv import example to specify DNA details - modify by pasting in your csv from this template: https://docs.google.com/spreadsheets/d/1ElzExoMNPRSHeEAxO5tCGN3aZAoJ3GVxH4ASsY3JF4I/edit?usp=sharing
csv_raw = '''DNA source,DNA destination,Plate destination,Transfection type,Contents,Concentration (ng/uL),DNA wanted (ng)
A1,B1,A1,Single,mNG,124.2,500
A2,B2,A2,Single,mKO2,179.9,500
A1,B3,A3,Co,mNG,124.2,250
A2,B3,A3,Co,mKO2,179.9,250
A3,B4,A4,Single,pGW0127,209,500
A4,B5,A5,Single,pGW0132,253,500
A5,B6,A6,Single,pGW0142,198,500'''

csv_data = csv_raw.splitlines()
csv_reader = csv.DictReader(csv_data)

# initialize lists - csv_reader is a dictionary, so I'm using lists here because I need indexing power
DNA_sources, DNA_dests, plate_dests,transfection_types, tube_names, uL_DNA, uL_OM, uL_P3K, uL_L3K = [],[],[],[],[],[],[],[],[]

for a in csv_reader:
    # convert parts of csv_reader, which is a dictionary, to a list which has indices
    DNA_sources.append(a['DNA source'])
    DNA_dests.append(a['DNA destination'])
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
    tuberack = protocol.load_labware(
        "opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap", location="1"
    )

    plate = protocol.load_labware(
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
        source_well = DNA_sources[a]
        destination_well = DNA_dests[a]
        DNA_vol = uL_DNA[a]

        # if/else for choosing the appropriate pipette to use
        if DNA_vol >= 20:
            right_pipette.transfer(
                volume = DNA_vol,
                source = tuberack[source_well],
                dest = tuberack[destination_well],
                mix_before = (3, 25), # mixes source well before aspiration 3 times with 25 uL volume
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'always'
                ) 

        else:
            left_pipette.transfer(
                volume = DNA_vol,
                source = tuberack[source_well],
                dest = tuberack[destination_well],
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
            source = tuberack['D5'],
            dest = tuberack['D3'],
            blow_out = True,
            blowout_location = 'destination well',
            new_tip = 'always'
            )
        
    else:
        left_pipette.transfer(
            volume = P3K_MM_vol,
            source = tuberack['D5'],
            dest = tuberack['D3'],
            blow_out = True,
            blowout_location = 'destination well',
            new_tip = 'always'
            )

    # Opti-MEM reagent pipetting
    if OM_MM_vol >= 20:
        right_pipette.transfer(
            volume = OM_MM_vol,
            source = tuberack['D6'],
            dest = tuberack['D3'],
            mix_after = (3,OM_MM_vol),
            blow_out = True,
            blowout_location = 'destination well',
            new_tip = 'always'
            )
        
    else:
        left_pipette.transfer(
            volume = OM_MM_vol,
            source = tuberack['D6'],
            dest = tuberack['D3'],
            mix_after = (3,OM_MM_vol),
            blow_out = True,
            blowout_location = 'destination well',
            new_tip = 'always'
            )

    # distribute OM/P3K MM to DNA dest tubes, which have DNA in them
    for a in range(len(DNA_dests)): 
        OM_P3K_MM_vol = uL_OM[a]+uL_P3K[a]
        source_well = 'D3'
        destination_well = DNA_dests[a]

        if OM_P3K_MM_vol >= 20:
            right_pipette.transfer(
                volume = OM_P3K_MM_vol,
                source = tuberack[source_well],
                dest = tuberack[destination_well],
                mix_after = (3, OM_P3K_MM_vol),
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'always'
                )
        else:
            left_pipette.transfer(
                volume = OM_P3K_MM_vol,
                source = tuberack[source_well],
                dest = tuberack[destination_well],
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
            source = tuberack['D4'],
            dest = tuberack['D2'],
            blow_out = True,
            blowout_location = 'destination well',
            new_tip = 'always'
            )
        
    else:
        left_pipette.transfer(
            volume = L3K_MM_vol,
            source = tuberack['D4'],
            dest = tuberack['D2'],
            blow_out = True,
            blowout_location = 'destination well',
            new_tip = 'always'
            )

    # Opti-MEM pipetting    
    if OM_MM_vol >= 20:
        right_pipette.transfer(
            volume = OM_MM_vol,
            source = tuberack['D6'],
            dest = tuberack['D2'],
            mix_after = (3,OM_MM_vol),
            blow_out = True,
            blowout_location = 'destination well',
            new_tip = 'always'
            )
        
    else:
        left_pipette.transfer(
            volume = OM_MM_vol,
            source = tuberack['D6'],
            dest = tuberack['D2'],
            mix_after = (3,15),
            blow_out = True,
            blowout_location = 'destination well',
            new_tip = 'always'
            )

    # figure out where the last DNA dest tube is and set index for robot to continue
    last_tube = DNA_dests[-1] # by design of this program, the last tube is the last row in your spreadsheet - plz make sure this is indeed the case
    for a in range(len(wells)):
        if wells[a] == last_tube:
            index = a+1
            break
        else:
            index = ''

    # figure out how many unique DNA destination wells there are
    unique_dests = []
    for a in DNA_dests:
        if a not in unique_dests:
            unique_dests.append(a)

    # distribute OM/L3K MM to empty tubes
    right_pipette.pick_up_tip()
    left_pipette.pick_up_tip()
    
    count = 0
    for a in range(index,index+len(unique_dests)): #will throw an error if 'index' wasn't found from above
        try:
            trans_type = transfection_types[count]
        except:
            trans_type = 'blah'

        # if/else to deal with co-transfections
        if trans_type == 'Co':
            # gather all tubes that should be cotransfected together by appending their indicies; searching for tubes with the same 'DNA_dest' location
            cotrans_group_indices = [count]
            for b in range(count+1,len(DNA_dests)):
                if DNA_dests[count] == DNA_dests[b]:
                    cotrans_group_indices.append(b)

            OM_L3K_MM_vol = 0
            destination_well = wells[a]
            
            for c in cotrans_group_indices:
                OM_L3K_MM_vol += uL_OM[c]+uL_L3K[c]
            
            count += len(cotrans_group_indices)
        else:
            OM_L3K_MM_vol = uL_OM[count]+uL_L3K[count]

            count += 1        
            
        source_well = 'D2'
        destination_well = wells[a]

        if OM_L3K_MM_vol >= 20:
            right_pipette.transfer(
                volume = OM_L3K_MM_vol,
                source = tuberack[source_well],
                dest = tuberack[destination_well],
                blow_out = True,
                new_tip = 'never'
                )
        else:
            left_pipette.transfer(
                volume = OM_L3K_MM_vol,
                source = tuberack[source_well],
                dest = tuberack[destination_well],
                blow_out = True,
                new_tip = 'never'
                )     

    right_pipette.drop_tip()
    left_pipette.drop_tip()    

    # pipette OM/P3K/DNA mixture into OM/L3K mixture
    count = 0
    for a in range(index,index+len(unique_dests)):
        try:
            trans_type = transfection_types[count]
        except:
            trans_type = 'blah'

        # if/else to deal with co-transfections
        if trans_type == 'Co':
            # gather all tubes that should be cotransfected together by appending their indicies; searching for tubes with the same 'DNA_dest' location
            cotrans_group_indices = [count]
            for b in range(count+1,len(DNA_dests)):
                if DNA_dests[count] == DNA_dests[b]:
                    cotrans_group_indices.append(b)

            OM_P3K_DNA_MM_vol = 0
            source_well = DNA_dests[count]
            destination_well = wells[a]
            
            for c in cotrans_group_indices:
                OM_P3K_DNA_MM_vol += uL_DNA[c]+uL_OM[c]+uL_P3K[c]
            
            count += len(cotrans_group_indices)
            
        else:
            OM_P3K_DNA_MM_vol = uL_DNA[count]+uL_OM[count]+uL_P3K[count]
            source_well = DNA_dests[count]
            destination_well = wells[a]

            count += 1

        if OM_P3K_DNA_MM_vol >= 20:
            right_pipette.transfer(
                volume = OM_P3K_DNA_MM_vol,
                source = tuberack[source_well],
                dest = tuberack[destination_well],
                mix_after = (3,OM_P3K_DNA_MM_vol),
                blow_out = True,
                new_tip = 'always'
                )
            
        else:
            left_pipette.transfer(
                volume = OM_P3K_DNA_MM_vol,
                source = tuberack[source_well],
                dest = tuberack[destination_well],
                mix_after = (3,20),
                blow_out = True,
                new_tip = 'always'
                )

    # pause robot to allow time to get cells and incubate transfection mixes
    protocol.pause('Now, incubate the mixture for 10 mins and get your cells and place in the deck specified in the OT-2 protocol')

    # Step 3) Adding transfection mixes to cells
    count, index_ = 0, index
    while index_ in range(index,index+len(unique_dests)):
        try:
            trans_type = transfection_types[count]
        except:
            trans_type = 'blah'
            
        # if/else to deal with co-transfections
        if trans_type == 'Co':            
            # gather all tubes that should be cotransfected together by appending their indicies; searching for tubes with the same 'DNA_dest' location
            cotrans_group_indices = [count]
            for a in range(count+1,len(DNA_dests)):
                if DNA_dests[count] == DNA_dests[a]:
                    cotrans_group_indices.append(a)

            transfection_vol = 0
            source_well = wells[index_]
            destination_well = plate_dests[count]
            for a in cotrans_group_indices:
                transfection_vol += (uL_DNA[a]+uL_OM[a]*2+uL_P3K[a]*2)/Excess
            
            index_ += 1
            count += len(cotrans_group_indices)        

        else:
            transfection_vol = (uL_DNA[count]+uL_OM[count]*2+uL_P3K[count]*2)/Excess
            source_well = wells[index_] 
            destination_well = plate_dests[count]
            
            index_ += 1
            count += 1

        if transfection_vol >= 20:
            right_pipette.transfer(
                volume = transfection_vol,
                source = tuberack[source_well],
                dest = plate[destination_well],
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'always'
                )
            
        else:
            left_pipette.transfer(
                volume = transfection_vol,
                source = tuberack[source_well],
                dest = plate[destination_well],
                blow_out = True,
                blowout_location = 'destination well',
                new_tip = 'always'
                )
        












    


    
