"""
CAPEX assessment tools for linearization and plotting of Z_tot for CO2 and DMS cycles.
The results are used in the Supplementary Material of the article of the scientific article.
"""
import matplotlib.pyplot as plt
import numpy as np

# CO2 constants for linearization
A = 60 #kW
B = 175 #kW
C_POWER = 2105.0
P_POWER = 0.4488
C_LINEAR_1 = 10908.0
C_LINEAR_2 = 115.744
C_OFFSET = 411.12
CO2_LINEAR_FACTOR = 1.5

# DMS constants for linearization
DMS_A = 4.0 #kW
DMS_B = 12.0 #kW
DMS_C_POWER = 8642.4
DMS_P_POWER = 0.46
DMS_C_LINEAR_1 = 77.91
DMS_C_LINEAR_2 = 1999.0
DMS_P_LINEAR = 0.6


def linearize_Z_tot_CO2_on_interval(a=A, b=B, n_samples=200, plot=True, force_intercept_zero=False):
	"""Linearize Z_tot on [a, b] using least squares and quantify fit quality.

	Z_tot = C_POWER * W_comp^P_POWER + C_LINEAR_1 * W_comp + CO2_LINEAR_FACTOR * (C_LINEAR_2 * W_comp + C_OFFSET)

	force_intercept_zero : bool, optional
		If True, force intercept = 0 (fit y = slope * x). Default is False.

	Returns
	-------
	tuple
		(linear_func, slope, intercept, metrics)
	"""
	if a >= b:
		raise ValueError("a must be < b")
	if n_samples < 2:
		raise ValueError("n_samples must be >= 2")

	x = np.linspace(a, b, n_samples)
	y = (
		C_POWER * np.power(x, P_POWER)
		+ C_LINEAR_1 * x
		+ CO2_LINEAR_FACTOR * (C_LINEAR_2 * x + C_OFFSET)
	)

	# Least-squares line: y = slope * x + intercept
	if force_intercept_zero:
		slope = np.dot(x, y) / np.dot(x, x)
		intercept = 0.0
	else:
		slope, intercept = np.polyfit(x, y, 1)
	y_lin = slope * x + intercept

	residuals = y - y_lin
	rmse = np.sqrt(np.mean(residuals**2))
	mae = np.mean(np.abs(residuals))
	max_abs_err = np.max(np.abs(residuals))
	ss_res = np.sum(residuals**2)
	ss_tot = np.sum((y - np.mean(y))**2)
	r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan

	metrics = {
		"rmse": rmse,
		"mae": mae,
		"max_abs_err": max_abs_err,
		"r2": r2,
	}

	def linear_func(x_val):
		return slope * x_val + intercept

	if plot:
		fig, axes = plt.subplots(2, 1, figsize=(9, 8), sharex=True)

		power_label = (
			rf"$Z_{{\mathrm{{CO_2}}}}={C_POWER:.4g}\,\dot{{W}}_{{\mathrm{{comp}}}}^{{{P_POWER:.4g}}}"
			rf"+{C_LINEAR_1:.4g}\,\dot{{W}}_{{\mathrm{{comp}}}}"
			rf"+{CO2_LINEAR_FACTOR:.4g}\,({C_LINEAR_2:.4g}\,\dot{{W}}_{{\mathrm{{comp}}}}+{C_OFFSET:.4g})$"
		)
		if force_intercept_zero:
			linear_label = r"$\hat{f}(x)=a x$" + f" | a={slope:.4g}"
		else:
			linear_label = r"$\hat{f}(x)=a x + b$" + f" | a={slope:.4g}, b={intercept:.4g}"

		axes[0].plot(x, y, label=power_label, linewidth=2)
		axes[0].plot(x, y_lin, label=linear_label, linestyle="--", linewidth=2)
		axes[0].set_ylabel(r"$Z_{\mathrm{CO_2}}$")
		axes[0].set_title("CAPEX of the CO_2 main cycle (Z_CO_2) linearization on " + f"[{a:.4g}, {b:.4g}]")
		axes[0].grid(True, alpha=0.3)
		axes[0].legend()

		axes[1].plot(x, residuals, color="tab:red")
		axes[1].axhline(0.0, color="black", linewidth=1)
		axes[1].set_xlabel(r"$\dot{W}_{\mathrm{comp}}$")
		axes[1].set_ylabel("residual")
		axes[1].grid(True, alpha=0.3)

		plt.tight_layout()
		plt.show()

	print("Linear fit: Z_tot = {:.6g} * W_comp + {:.6g}".format(slope, intercept))
	print("Metrics: RMSE={:.6g}, MAE={:.6g}, max|err|={:.6g}, R2={:.6g}".format(
		metrics["rmse"], metrics["mae"], metrics["max_abs_err"], metrics["r2"]
	))

	return linear_func, slope, intercept, metrics


def linearize_Z_tot_DMS_on_interval(a=DMS_A, b=DMS_B, n_samples=200, plot=True, force_intercept_zero=False):
	"""Linearize Z_tot for DMS on [a, b] using least squares and quantify fit quality.

	Z_tot = DMS_C_POWER * W_comp^DMS_P_POWER
		+ DMS_C_LINEAR_1 * W_comp^DMS_P_LINEAR
		+ DMS_C_LINEAR_2 * W_comp^DMS_P_LINEAR

	force_intercept_zero : bool, optional
		If True, force intercept = 0 (fit y = slope * x). Default is False.

	Returns
	-------
	tuple
		(linear_func, slope, intercept, metrics)
	"""
	if a >= b:
		raise ValueError("a must be < b")
	if n_samples < 2:
		raise ValueError("n_samples must be >= 2")

	x = np.linspace(a, b, n_samples)

	y = (
		DMS_C_POWER * np.power(x, DMS_P_POWER)
		+ DMS_C_LINEAR_1 * np.power(x, DMS_P_LINEAR)
		+ DMS_C_LINEAR_2 * np.power(x, DMS_P_LINEAR)
	)

	# Least-squares line: y = slope * x + intercept
	if force_intercept_zero:
		slope = np.dot(x, y) / np.dot(x, x)
		intercept = 0.0
	else:
		slope, intercept = np.polyfit(x, y, 1)
	y_lin = slope * x + intercept

	residuals = y - y_lin
	rmse = np.sqrt(np.mean(residuals**2))
	mae = np.mean(np.abs(residuals))
	max_abs_err = np.max(np.abs(residuals))
	ss_res = np.sum(residuals**2)
	ss_tot = np.sum((y - np.mean(y))**2)
	r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan

	metrics = {
		"rmse": rmse,
		"mae": mae,
		"max_abs_err": max_abs_err,
		"r2": r2,
	}

	def linear_func(x_val):
		return slope * x_val + intercept

	if plot:
		fig, axes = plt.subplots(2, 1, figsize=(9, 8), sharex=True)

		power_label = (
			rf"$Z_{{\mathrm{{DMS}}}}={DMS_C_POWER:.4g}\,\dot{{W}}_{{\mathrm{{comp}}}}^{{{DMS_P_POWER:.4g}}}"
			rf"+{DMS_C_LINEAR_1:.4g}\,\dot{{W}}_{{\mathrm{{comp}}}}^{{{DMS_P_LINEAR:.4g}}}"
			rf"+{DMS_C_LINEAR_2:.4g}\,\dot{{W}}_{{\mathrm{{comp}}}}^{{{DMS_P_LINEAR:.4g}}}$"
		)
		if force_intercept_zero:
			linear_label = r"$\hat{f}(x)=a x$" + f" | a={slope:.4g}"
		else:
			linear_label = r"$\hat{f}(x)=a x + b$" + f" | a={slope:.4g}, b={intercept:.4g}"

		axes[0].plot(x, y, label=power_label, linewidth=2)
		axes[0].plot(x, y_lin, label=linear_label, linestyle="--", linewidth=2)
		axes[0].set_ylabel(r"$Z_{\mathrm{DMS}}$")
		axes[0].set_title("CAPEX of the propane cycle (DMS) (Z_DMS) linearization on " + f"[{a:.4g}, {b:.4g}]")
		axes[0].grid(True, alpha=0.3)
		axes[0].legend()

		axes[1].plot(x, residuals, color="tab:red")
		axes[1].axhline(0.0, color="black", linewidth=1)
		axes[1].set_xlabel(r"$\dot{W}_{\mathrm{comp}}$")
		axes[1].set_ylabel("residual")
		axes[1].grid(True, alpha=0.3)

		plt.tight_layout()
		plt.show()

	print("Linear fit: Z_tot = {:.6g} * W_comp + {:.6g}".format(slope, intercept))
	print("Metrics: RMSE={:.6g}, MAE={:.6g}, max|err|={:.6g}, R2={:.6g}".format(
		metrics["rmse"], metrics["mae"], metrics["max_abs_err"], metrics["r2"]
	))

	return linear_func, slope, intercept, metrics


# if __name__ == "__main__":
	# linearize_Z_tot_CO2_on_interval(force_intercept_zero=False, n_samples=300, plot=True)
	# linearize_Z_tot_DMS_on_interval(force_intercept_zero=False, n_samples=300, plot=True)




