"""Axial datums and running clearances in millimetres."""
from math import asin, atan2, ceil, degrees, floor, hypot


GATE_THICKNESS_MM = 38.
CHANNEL_SECTION_MM = (158., 65.)
CHANNEL_FLOOR_MM = -30.5
OUTLET_R_MM = 3.
ENTRY_TRANSITION_MM = 5.


def layout(frame, upstream, product, curve, thickness_mm=GATE_THICKNESS_MM,
           working_travel_mm=75., axial_allowance_mm=0.):
    axis = upstream['axis_A']
    gate = upstream['gate']
    cast = frame['traverses']['chamber']
    interface = frame['interfaces']
    face_mm = axis['closed_gate_inner_face_x_mm']
    rear_mm = face_mm + thickness_mm
    insert_mm = interface['insert_depth_mm']
    channel_mm = cast['depth_mm']
    width_mm, height_mm = upstream['main_section_mm']
    recovery = curve['transverse_area_growth']
    max_width_mm, max_height_mm = width_mm*(1+recovery), height_mm*(1+recovery)
    limiting = min((row['travel_overrun_mm']-row['axial_growth_mm'], dose, regime, material)
                   for dose, cases in gate['clearance_cases'].items()
                   for regime, materials in cases.items() for material,row in materials.items())
    upper_recovery_mm = max(row['axial_growth_mm'] for materials in gate['clearance_cases']['upper_dose'].values()
                            for row in materials.values())
    required_axial_mm = gate['axial_clearance_mm']
    travel_add_mm = max(0, ceil(thickness_mm+required_axial_mm+axial_allowance_mm-limiting[0]))
    nominal_back_clearance_mm = (gate['nominal_overtravel_mm']+travel_add_mm-thickness_mm
                                 -gate['clearance_cases']['nominal']['nominal']['base']['axial_growth_mm'])
    minimum_axial_clearance_mm = limiting[0]+travel_add_mm-thickness_mm
    channel_ceiling_mm = CHANNEL_FLOOR_MM + CHANNEL_SECTION_MM[1]
    # For a 40-mm part initially aligned with the rails, the first crossing
    # of width cos(theta) + length sin(theta) = opening limits its excursion.
    def first_rotation_deg(narrow_mm, opening_mm):
        return degrees(asin(opening_mm/hypot(narrow_mm,40.)) - atan2(narrow_mm,40.))

    shortening_mm = interface['open_discharge_bay_mm'] + insert_mm - (thickness_mm-GATE_THICKNESS_MM)
    max_product_mm = [a+product['tol_mm'] for a in product['value_mm']]
    qualified_guide_width_mm = max_product_mm[0]+1.
    min_compliant_width_mm = width_mm-product['tol_mm']
    corner_cast_mm = [CHANNEL_SECTION_MM[0]/2-OUTLET_R_MM, channel_ceiling_mm-OUTLET_R_MM]
    r20_clearance_mm = 20.-OUTLET_R_MM-hypot(corner_cast_mm[0]-(176./2-20.),corner_cast_mm[1]-(74./2-20.))
    return {
        'main_stroke_increment_mm': travel_add_mm,
        'axial_allowance_mm': axial_allowance_mm,
        'minimum_relaxed_tail_clearance_after_allowance_mm': minimum_axial_clearance_mm-axial_allowance_mm,
        'gate_face_x_mm': face_mm,
        'gate_back_x_mm': rear_mm,
        'original_cast_face_x_mm': rear_mm+shortening_mm,
        'closed_gate_thickness_mm': thickness_mm,
        'insert_seat_face_x_mm': rear_mm,
        'insert_recess_depth_mm': insert_mm,
        'channel_length_mm': channel_mm,
        'channel_exit_x_mm': rear_mm+channel_mm,
        'passage_inlet_mm': list(CHANNEL_SECTION_MM),
        'passage_exit_mm': list(CHANNEL_SECTION_MM),
        'cast_channel_mm_R': [176., 74., 20.],
        'guide_corner_clearance_in_cast_R20_mm': r20_clearance_mm,
        'bored_gate_and_insert_R_mm': OUTLET_R_MM,
        'entry_transition_max_loaded_length_mm': ENTRY_TRANSITION_MM,
        'guide_floor_y_mm': CHANNEL_FLOOR_MM,
        'guide_ceiling_y_mm': channel_ceiling_mm,
        'nominal_floor_step_down_mm': -height_mm/2-CHANNEL_FLOOR_MM,
        'open_window_center_y_mm': CHANNEL_FLOOR_MM+CHANNEL_SECTION_MM[1]/2,
        'closed_window_center_y_mm': CHANNEL_FLOOR_MM+CHANNEL_SECTION_MM[1]/2-working_travel_mm,
        'closed_window_ligament_to_chamber_mm': -height_mm/2-(channel_ceiling_mm-working_travel_mm),
        'gate_working_travel_mm': working_travel_mm,
        'punch_face_nominal_eject_end_x_mm': (axis['punch_ejection_end_x_mm']+travel_add_mm),
        'punch_face_maximum_eject_end_x_mm': axis['max_operating_travel_mm']+travel_add_mm,
        'main_installed_stroke_mm': axis['main_installed_stroke_mm']+travel_add_mm,
        'overtravel_nominal_mm': gate['nominal_overtravel_mm']+travel_add_mm,
        'overtravel_maximum_mm': gate['max_overtravel_mm']+travel_add_mm,
        'nominal_relaxed_tail_clearance_mm': nominal_back_clearance_mm,
        'minimum_relaxed_tail_clearance_mm': minimum_axial_clearance_mm,
        'maximum_gate_thickness_preserving_5mm_axial_margin_mm': limiting[0]-required_axial_mm,
        'limiting_tail_case': list(limiting[1:]),
        'maximum_tail_springback_mm': upper_recovery_mm,
        'max_compliant_product_section_mm': max_product_mm,
        'equal_transverse_strain_section_mm': [d*(1+recovery)**.5 for d in (width_mm,height_mm)],
        'max_recovered_section_axiswise_mm': [max_width_mm,max_height_mm],
        'side_clearance_per_side_after_max_recovery_mm': (CHANNEL_SECTION_MM[0]-max_width_mm)/2,
        'top_clearance_after_max_recovery_at_floor_mm': CHANNEL_SECTION_MM[1]-max_height_mm,
        'shortest_product_mm': 40.,
        'shortest_loaded_product_at_project_recovery_mm': 40./(1+max(curve['springback'].values())),
        'unlined_passage_prevents_yaw_of_40mm_product': CHANNEL_SECTION_MM[0] < hypot(width_mm,40.),
        'qualified_lot_guide_width_mm': qualified_guide_width_mm,
        'qualified_lot_max_short_yaw_deg': first_rotation_deg(min_compliant_width_mm,qualified_guide_width_mm),
        'lot_guide_width_condition': 'width_max + 1 mm <= set_width < hypot(width_min, minimum_free_length) - 0.5 mm',
        'typical_max_short_pitch_deg': first_rotation_deg(height_mm, CHANNEL_SECTION_MM[1]),
        'punch_face_clear_for_gate_close_x_mm': face_mm-10.,
        'guide_to_punch_lever_mm': interface['layout']['guide_to_punch_lever_mm'],
        'column_shortening_mm': shortening_mm,
        'frame_axial_length_mm': interface['layout']['frame_axial_length_mm']-shortening_mm,
        'column_smooth_span_mm': frame['columns']['smooth_span_mm']-shortening_mm,
        'inner_bearing_spacing_mm': interface['inner_bearing_planes_spacing_mm']-shortening_mm,
        'module_envelope_xyz_mm': [interface['layout']['module_axial_excluding_ZSF_and_safety_guards_mm']-shortening_mm+travel_add_mm,
                                   interface['layout']['frame_transverse_max_mm'],
                                   interface['layout']['frame_height_with_feet_upper_mm']],
        'stack_counts': [
            {'length_mm': length_mm, 'whole_briquettes': floor(channel_mm/length_mm),
             'maximum_simultaneous_with_end_pieces': ceil(channel_mm/length_mm)+1,
             'first_exit_cycles_from_empty': ceil((channel_mm-((axis['punch_ejection_end_x_mm']+travel_add_mm)-rear_mm))/length_mm)}
            for length_mm in (40,110)],
    }


