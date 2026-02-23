"""
Compressor isentropic efficiency plots for the 2 different fluids that are used in the main cycle (CO2) and in the DMS system (propane).
"""
import matplotlib.pyplot as plt
import numpy as np

# Global refrigerant names
REFRIGERANTS = ['R744', 'R290']

# Global polynomial coefficients for efficiency calculation (degree 3)
EFFICIENCY_COEFFICIENTS = {
    'R744': [1.003, -0.121, 0., 0.],       # CO2
    'R290': [0.3774, 0.1405, -0.0201, 0.0008],      # Propane
}

# Global color mapping for refrigerants
REFRIGERANT_COLORS = {
    'R744': 'orange',
    'R290': 'green',
}

def plot_global_efficiencies(coefficients=EFFICIENCY_COEFFICIENTS, colors=REFRIGERANT_COLORS):
    """
    Plot global efficiencies of different refrigerants as a function of compression ratio.
    Coefficients are defined for 3rd degree polynomials.
    
    Args:
        coefficients (dict): Dictionary of polynomial coefficients for each refrigerant
        colors (dict): Dictionary of colors for each refrigerant curve
    """
    
    # Compression ratio range
    x = np.linspace(1, 5, 300)
    
    # Create figure
    plt.figure(figsize=(12, 7))

    # Labels
    label_R744 = 'R744 - CO2 (main cycle)' 
    label_R290 = 'R290 - Propane (DMS system)'
    
    # Plot each curve
    for refrigerant, coefs in coefficients.items():
        # Calculate polynomial y = a + b*x + c*x² + d*x³
        y = np.polyval(coefs[::-1], x)  # polyval expects coefficients from highest to lowest degree
        color = colors.get(refrigerant, 'black')  # Default to black if color not specified
        
        label = label_R744 if refrigerant == 'R744' else label_R290
                
        plt.plot(x, y, 
                 label=f'{label}', 
                 color=color, 
                 linewidth=2)
        
        # Display equation in legend
        equation = f"y = {coefs[0]:.4f} + {coefs[1]:.4f}x + {coefs[2]:.4f}x² + {coefs[3]:.4f}x³"
        print(f"{refrigerant}: {equation}")
    
    # Configure plot
    plt.title('Compressor global efficiency of the refrigerants used', 
              fontsize=16, fontweight='bold', pad=20)
    plt.xlabel('Compression ratio (-)', fontsize=12)
    plt.ylabel('η_global (-)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend(loc='best', fontsize=11)
    
    # Axis limits
    plt.xlim(1, 5)
    
    # Auto-adjust y-axis limits to better show differences
    plt.ylim(0, 1.2)
    
    # Display
    plt.tight_layout()
    plt.show()
    
    return coefficients

def calculate_global_efficiency(refrigerant, compression_ratio, coefficients=EFFICIENCY_COEFFICIENTS):
    """
    Calculate the global efficiency for a given refrigerant and compression ratio.
    
    Args:
        refrigerant (str): Name of refrigerant ('R134a', 'R1234yf', 'R600a', 'R290', etc.)
        compression_ratio (float): Compression ratio
        coefficients (dict): Dictionary of polynomial coefficients for each refrigerant
        
    Returns:
        float: Calculated global efficiency
        
    Raises:
        ValueError: If refrigerant is not in the coefficients dictionary
    """
    if refrigerant not in coefficients:
        raise ValueError(f"Refrigerant {refrigerant} not recognized. Options: {list(coefficients.keys())}")
    
    coefs = coefficients[refrigerant]
    # Apply polynomial formula: y = a + b*x + c*x² + d*x³
    efficiency = (coefs[0] + 
                 coefs[1] * compression_ratio + 
                 coefs[2] * compression_ratio**2 + 
                 coefs[3] * compression_ratio**3)
    
    return efficiency

############################################# EXECUTION #############################################

coeffs = plot_global_efficiencies(EFFICIENCY_COEFFICIENTS, REFRIGERANT_COLORS)


