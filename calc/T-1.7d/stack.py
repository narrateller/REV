"""Upper and lower ejection forces for the guided, free outlet."""
from dataclasses import dataclass
from math import expm1


@dataclass(frozen=True)
class Stack:
    length_mm: float
    section_mm: tuple[float, float]
    transition_mm: float
    local_pressure_MPa: float
    die_length_mm: float
    growth_mm: float
    engagement_mm: float
    stroke_mm: float
    die_drag_N: float
    mu: float
    crumbs_N: float
    mass_kg: float
    side_guide_normal_weight_ratio: float
    effective_wall_pressure_MPa: float = 0.

    @property
    def perimeter_mm(self):
        return 2*sum(self.section_mm)

    @property
    def local_force_N(self):
        return self.mu*self.local_pressure_MPa*self.perimeter_mm*self.transition_mm

    @property
    def gravity_force_N(self):
        return self.mu*self.mass_kg*9.81*(1+self.side_guide_normal_weight_ratio)

    def transition_force_N(self, displacement_mm):
        # A short conservative full-perimeter band at the die exit. Fade in
        # over one millimetre and remove it after the rear clears the band.
        return self.local_force_N*min(1.,max(0.,displacement_mm))*min(
            1.,max(0.,self.die_length_mm + self.transition_mm - displacement_mm))

    def force_N(self, displacement_m):
        x_mm = 1000*displacement_m
        engaged = min(1.,max(0.,x_mm-self.engagement_mm))
        return self.transition_force_N(x_mm)+engaged*(
            self.crumbs_N+self.gravity_force_N+
            self.mu*self.effective_wall_pressure_MPa*self.perimeter_mm*self.length_mm)

    def total_force_N(self, displacement_m, guide_drag_N):
        return guide_drag_N+self.die_drag_N*max(0.,1.-1000*displacement_m/self.die_length_mm)+self.force_N(displacement_m)

    def peak(self, guide_drag_N):
        points_mm = (0., 1., self.engagement_mm, self.engagement_mm+1.,
                     self.die_length_mm, self.die_length_mm+self.transition_mm-1.,
                     self.die_length_mm+self.transition_mm,self.stroke_mm)
        return max((self.total_force_N(x_mm/1000,guide_drag_N),x_mm)
                   for x_mm in points_mm if 0. <= x_mm <= self.stroke_mm)


def from_reference(upstream, geometry, model, mu, crumbs_N, case, guide_weight_ratio, pressure_regime):
    loads = upstream['shoe_load']
    sample = loads['samples']['nominal'][pressure_regime][case]
    die_mm = model.die_length_m*1000
    growth_mm = die_mm*(model.material.axial_ratio(case)-1)
    p_MPa = sample['open_gate_ejection_start']['residual_radial_offset_MPa']
    recovered_density_kg_m3 = model.in_die_kg_m3/model.material.volume_ratio(case)
    section_mm = tuple(upstream['main_section_mm'])
    # Bound the supported weight using the in-die density, the full free
    # guide cross-section and one whole 110-mm piece overhanging the exit.
    max_supported_mass_kg = (model.in_die_kg_m3 * geometry['passage_exit_mm'][0] *
                             geometry['passage_exit_mm'][1]*(geometry['channel_length_mm']+110)*1e-9)
    engagement_mm = max(0., model.overtravel_m*1000-2*growth_mm)
    reconstructed_die_drag_N = (model.section_m2*1e6*p_MPa/sample['K'] *
                               expm1(sample['attenuation_per_mm']*sample['loaded_length_mm']))
    assert abs(reconstructed_die_drag_N-loads['ejection_resistance_N']) < 1e-5
    return Stack(geometry['channel_length_mm'],section_mm,geometry['entry_transition_max_loaded_length_mm'],
                 p_MPa,die_mm,growth_mm,engagement_mm,(model.main_travel_m-model.press_end_m)*1000,
                 loads['ejection_resistance_N'],mu,crumbs_N,max_supported_mass_kg,guide_weight_ratio), recovered_density_kg_m3
