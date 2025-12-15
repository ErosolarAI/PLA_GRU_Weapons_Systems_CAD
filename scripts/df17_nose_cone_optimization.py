#!/usr/bin/env python3
"""
DF-17 Hypersonic Glide Vehicle Nose Cone Optimization
Real CAD optimization for improved aerodynamic performance.
"""

import cadquery as cq
import numpy as np
from scipy.optimize import minimize
import matplotlib.pyplot as plt
from typing import Dict, Tuple
import json

class DF17NoseConeOptimizer:
    """Optimize DF-17 nose cone for hypersonic flight."""
    
    def __init__(self):
        # DF-17 specifications
        self.base_diameter = 880  # mm
        self.total_length = 10000  # mm
        self.nose_length = 2500  # mm
        
        # Material properties (Titanium alloy)
        self.material = {
            'density': 4.43,  # g/cm³
            'yield_strength': 830,  # MPa
            'thermal_conductivity': 21.9,  # W/m·K
            'max_temp': 1800  # °C
        }
        
        # Flight conditions
        self.flight_conditions = {
            'max_mach': 10,
            'max_dynamic_pressure': 50000,  # Pa
            'max_heat_flux': 5e6,  # W/m²
            'flight_time': 600  # seconds
        }
        
    def create_parametric_nose(self, parameters: Dict) -> cq.Workplane:
        """Create parametric nose cone geometry."""
        # Nose cone parameters
        radius = parameters.get('radius', self.base_diameter / 2)
        length = parameters.get('length', self.nose_length)
        
        # Nose shape parameters (0 = conical, 1 = parabolic, 2 = ogive)
        shape_factor = parameters.get('shape_factor', 1.5)
        
        # Create nose cone using parametric equations
        nose = (
            cq.Workplane("XY")
            .circle(radius)
            .workplane(offset=length)
            .circle(0.001)  # Tip radius
            .loft()
        )
        
        # Add thermal protection layer
        if parameters.get('thermal_protection', True):
            tps_thickness = parameters.get('tps_thickness', 25)  # mm
            tps = nose.faces("<Z").shell(-tps_thickness)
            nose = nose.union(tps)
        
        return nose
    
    def objective_function(self, x: np.ndarray) -> float:
        """Multi-objective optimization function."""
        parameters = {
            'radius': x[0],
            'length': x[1],
            'shape_factor': x[2],
            'tps_thickness': x[3]
        }
        
        # Calculate metrics
        drag = self.calculate_drag(parameters)
        heat_load = self.calculate_heat_load(parameters)
        mass = self.calculate_mass(parameters)
        stress = self.calculate_stress(parameters)
        
        # Weighted objective (minimize)
        weights = {
            'drag': 0.35,
            'heat': 0.25,
            'mass': 0.25,
            'stress': 0.15
        }
        
        # Normalize objectives
        drag_norm = drag / 5000  # Normalize to typical value
        heat_norm = heat_load / 1e7
        mass_norm = mass / 100
        stress_norm = stress / self.material['yield_strength']
        
        objective = (
            weights['drag'] * drag_norm +
            weights['heat'] * heat_norm +
            weights['mass'] * mass_norm +
            weights['stress'] * stress_norm
        )
        
        return objective
    
    def calculate_drag(self, parameters: Dict) -> float:
        """Calculate drag coefficient using empirical relations."""
        radius = parameters['radius']
        length = parameters['length']
        shape_factor = parameters['shape_factor']
        
        # Reference area
        S_ref = np.pi * radius**2
        
        # Shape-dependent drag coefficient
        # Conical: Cd ≈ 0.05, Parabolic: Cd ≈ 0.03, Ogive: Cd ≈ 0.02
        base_cd = 0.05 * np.exp(-0.5 * shape_factor)
        
        # Length-to-diameter ratio effect
        l_d_ratio = length / (2 * radius)
        cd_length_factor = 1.0 / (1.0 + 0.1 * l_d_ratio)
        
        # Mach number effect (hypersonic)
        mach = self.flight_conditions['max_mach']
        cd_mach_factor = 1.0 + 0.1 * (mach - 5)**2
        
        drag_coefficient = base_cd * cd_length_factor * cd_mach_factor
        dynamic_pressure = self.flight_conditions['max_dynamic_pressure']
        
        return drag_coefficient * dynamic_pressure * S_ref
    
    def calculate_heat_load(self, parameters: Dict) -> float:
        """Calculate thermal load on nose cone."""
        radius = parameters['radius']
        length = parameters['length']
        tps_thickness = parameters.get('tps_thickness', 25)
        
        # Stagnation point heat flux (Sutton-Graves equation)
        mach = self.flight_conditions['max_mach']
        r_nose = 0.01 * radius  # Nose radius in meters
        
        # Simplified hypersonic heat flux
        q_stag = 1.83e-4 * mach**3 * (1.0 / np.sqrt(r_nose))
        
        # Surface area
        surface_area = np.pi * radius * np.sqrt(radius**2 + length**2)
        
        # Thermal protection effectiveness
        tps_effectiveness = 1.0 - np.exp(-tps_thickness / 25)
        
        total_heat = q_stag * surface_area * (1.0 - tps_effectiveness)
        return total_heat
    
    def calculate_mass(self, parameters: Dict) -> float:
        """Calculate nose cone mass."""
        radius = parameters['radius']
        length = parameters['length']
        tps_thickness = parameters.get('tps_thickness', 25)
        
        # Structure volume (conical approximation)
        structure_volume = (1/3) * np.pi * radius**2 * length
        
        # TPS volume (shell)
        outer_radius = radius + tps_thickness
        tps_volume = (1/3) * np.pi * (outer_radius**2 - radius**2) * length
        
        # Material densities (g/cm³ to kg/mm³ conversion)
        density_structural = self.material['density'] * 1e-6  # kg/mm³
        density_tps = 2.2 * 1e-6  # C/SiC composite
        
        mass = (structure_volume * density_structural + 
                tps_volume * density_tps)
        
        return mass * 1000  # Convert to kg
    
    def calculate_stress(self, parameters: Dict) -> float:
        """Calculate structural stress."""
        radius = parameters['radius']
        length = parameters['length']
        
        # Aerodynamic pressure
        dynamic_pressure = self.flight_conditions['max_dynamic_pressure']
        
        # Bending moment (simplified)
        bending_moment = dynamic_pressure * np.pi * radius**2 * length / 4
        
        # Section modulus for thin-walled cone
        thickness = 10  # mm (structural thickness)
        section_modulus = np.pi * radius**2 * thickness
        
        bending_stress = bending_moment / section_modulus
        
        # Thermal stress (simplified)
        delta_t = 1500  # °C temperature gradient
        alpha = 8.6e-6  # Thermal expansion coefficient
        E = 113.8e3  # Young's modulus (MPa)
        
        thermal_stress = E * alpha * delta_t
        
        total_stress = bending_stress + thermal_stress
        return total_stress
    
    def optimize(self, generations: int = 100) -> Dict:
        """Run optimization using genetic algorithm."""
        print("Starting DF-17 nose cone optimization...")
        
        # Bounds for parameters [radius, length, shape_factor, tps_thickness]
        bounds = [
            (400, 500),    # radius (mm)
            (2000, 3000),  # length (mm)
            (0.5, 2.5),    # shape_factor
            (20, 50)       # tps_thickness (mm)
        ]
        
        # Initial guess
        x0 = [440, 2500, 1.5, 25]
        
        # Constraints
        constraints = [
            {'type': 'ineq', 'fun': lambda x: self.material['yield_strength'] - self.calculate_stress({
                'radius': x[0], 'length': x[1], 'tps_thickness': x[3]
            })},
            {'type': 'ineq', 'fun': lambda x: 200 - self.calculate_mass({
                'radius': x[0], 'length': x[1], 'tps_thickness': x[3]
            })},  # Max 200kg
        ]
        
        # Run optimization
        result = minimize(
            self.objective_function,
            x0,
            bounds=bounds,
            constraints=constraints,
            method='SLSQP',
            options={'maxiter': generations, 'disp': True}
        )
        
        # Extract optimized parameters
        optimized_params = {
            'radius': result.x[0],
            'length': result.x[1],
            'shape_factor': result.x[2],
            'tps_thickness': result.x[3],
            'objective_value': result.fun,
            'success': result.success
        }
        
        # Calculate performance metrics
        metrics = self.calculate_performance_metrics(optimized_params)
        optimized_params.update(metrics)
        
        return optimized_params
    
    def calculate_performance_metrics(self, parameters: Dict) -> Dict:
        """Calculate detailed performance metrics."""
        return {
            'drag_force_N': self.calculate_drag(parameters),
            'heat_load_W': self.calculate_heat_load(parameters),
            'mass_kg': self.calculate_mass(parameters),
            'stress_MPa': self.calculate_stress(parameters),
            'safety_factor': self.material['yield_strength'] / self.calculate_stress(parameters),
            'drag_reduction_percent': self.calculate_drag_reduction(parameters),
            'mass_reduction_percent': self.calculate_mass_reduction(parameters)
        }
    
    def calculate_drag_reduction(self, parameters: Dict) -> float:
        """Calculate drag reduction compared to baseline."""
        baseline_params = {
            'radius': self.base_diameter / 2,
            'length': self.nose_length,
            'shape_factor': 1.0,
            'tps_thickness': 30
        }
        
        baseline_drag = self.calculate_drag(baseline_params)
        optimized_drag = self.calculate_drag(parameters)
        
        return ((baseline_drag - optimized_drag) / baseline_drag) * 100
    
    def calculate_mass_reduction(self, parameters: Dict) -> float:
        """Calculate mass reduction compared to baseline."""
        baseline_params = {
            'radius': self.base_diameter / 2,
            'length': self.nose_length,
            'shape_factor': 1.0,
            'tps_thickness': 30
        }
        
        baseline_mass = self.calculate_mass(baseline_params)
        optimized_mass = self.calculate_mass(parameters)
        
        return ((baseline_mass - optimized_mass) / baseline_mass) * 100
    
    def generate_cad_model(self, parameters: Dict, filename: str = "df17_nose_optimized.step"):
        """Generate and export optimized CAD model."""
        print(f"Generating CAD model: {filename}")
        
        # Create optimized geometry
        nose_cone = self.create_parametric_nose(parameters)
        
        # Add mounting interface
        mount = (
            cq.Workplane("XY")
            .workplane(offset=-50)
            .circle(parameters['radius'])
            .extrude(50)
        )
        
        # Combine parts
        assembly = nose_cone.union(mount)
        
        # Export to STEP format
        cq.exporters.export(assembly, f"cad_models/df17/optimized/{filename}")
        
        # Also export STL for 3D printing/visualization
        cq.exporters.export(assembly, f"cad_models/df17/optimized/{filename.replace('.step', '.stl')}")
        
        print(f"CAD model exported to cad_models/df17/optimized/{filename}")
        return assembly
    
    def plot_optimization_results(self, parameters: Dict, history: list = None):
        """Plot optimization results and performance metrics."""
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        
        # Nose cone geometry
        ax1 = axes[0, 0]
        radii = np.linspace(0, parameters['length'], 100)
        profile = parameters['radius'] * (1 - (radii / parameters['length'])**parameters['shape_factor'])
        ax1.plot(radii, profile, 'b-', linewidth=2)
        ax1.plot(radii, -profile, 'b-', linewidth=2)
        ax1.set_xlabel('Length (mm)')
        ax1.set_ylabel('Radius (mm)')
        ax1.set_title('Optimized Nose Cone Profile')
        ax1.grid(True)
        ax1.axis('equal')
        
        # Performance metrics
        ax2 = axes[0, 1]
        metrics = ['Drag', 'Heat Load', 'Mass', 'Stress']
        values = [
            parameters.get('drag_force_N', 0) / 1000,
            parameters.get('heat_load_W', 0) / 1e6,
            parameters.get('mass_kg', 0),
            parameters.get('stress_MPa', 0)
        ]
        bars = ax2.bar(metrics, values)
        ax2.set_ylabel('Value')
        ax2.set_title('Performance Metrics')
        ax2.grid(True, alpha=0.3)
        
        # Color bars by value (red for high, green for low)
        for bar, value in zip(bars, values):
            if 'Drag' in bar.get_label() or 'Stress' in bar.get_label():
                bar.set_color('lightcoral' if value > np.mean(values) else 'lightgreen')
            else:
                bar.set_color('lightgreen' if value < np.mean(values) else 'lightcoral')
        
        # Improvements
        ax3 = axes[0, 2]
        improvements = ['Drag Reduction', 'Mass Reduction']
        improvement_values = [
            parameters.get('drag_reduction_percent', 0),
            parameters.get('mass_reduction_percent', 0)
        ]
        ax3.bar(improvements, improvement_values, color=['green', 'blue'])
        ax3.set_ylabel('Improvement (%)')
        ax3.set_title('Optimization Improvements')
        ax3.grid(True, alpha=0.3)
        
        # Material properties
        ax4 = axes[1, 0]
        material_props = ['Density', 'Yield Strength', 'Max Temp']
        material_values = [
            self.material['density'],
            self.material['yield_strength'],
            self.material['max_temp']
        ]
        ax4.bar(material_props, material_values, color=['orange', 'red', 'darkred'])
        ax4.set_ylabel('Value')
        ax4.set_title('Material Properties (Titanium Alloy)')
        ax4.grid(True, alpha=0.3)
        
        # Flight conditions
        ax5 = axes[1, 1]
        flight_params = ['Max Mach', 'Max Q', 'Max Heat Flux']
        flight_values = [
            self.flight_conditions['max_mach'],
            self.flight_conditions['max_dynamic_pressure'] / 1000,
            self.flight_conditions['max_heat_flux'] / 1e6
        ]
        ax5.bar(flight_params, flight_values, color=['purple', 'cyan', 'magenta'])
        ax5.set_ylabel('Value')
        ax5.set_title('Flight Conditions')
        ax5.grid(True, alpha=0.3)
        
        # Optimization convergence (if history provided)
        if history:
            ax6 = axes[1, 2]
            ax6.plot(history, 'r-', linewidth=2)
            ax6.set_xlabel('Iteration')
            ax6.set_ylabel('Objective Value')
            ax6.set_title('Optimization Convergence')
            ax6.grid(True)
        
        plt.tight_layout()
        plt.savefig('optimization_results.png', dpi=300, bbox_inches='tight')
        plt.show()


def main():
    """Main execution function."""
    print("="*70)
    print("DF-17 HYPERSONIC GLIDE VEHICLE NOSE CONE OPTIMIZATION")
    print("="*70)
    
    # Initialize optimizer
    optimizer = DF17NoseConeOptimizer()
    
    # Run optimization
    print("\nRunning optimization...")
    optimized_params = optimizer.optimize(generations=200)
    
    # Display results
    print("\n" + "="*70)
    print("OPTIMIZATION RESULTS")
    print("="*70)
    
    print(f"\nOptimized Parameters:")
    print(f"  Radius: {optimized_params['radius']:.1f} mm")
    print(f"  Length: {optimized_params['length']:.1f} mm")
    print(f"  Shape Factor: {optimized_params['shape_factor']:.3f}")
    print(f"  TPS Thickness: {optimized_params['tps_thickness']:.1f} mm")
    
    print(f"\nPerformance Metrics:")
    print(f"  Drag