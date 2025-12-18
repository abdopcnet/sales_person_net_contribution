// Payment Entry Client Script
// Add button to calculate net contribution and update Sales Invoice Sales Team

frappe.ui.form.on('Payment Entry', {
	refresh: function (frm) {
		// Calculate custom fields in references table
		calculate_reference_fields(frm);

		// Add direct button to calculate net contribution (green button)
		// Only show button for submitted documents with payment_type = "Receive"
		if (frm.doc.docstatus === 1 && frm.doc.payment_type === 'Receive') {
			frm.page.add_inner_button(
				__('تحديث نسبة المندوب'),
				function () {
					calculate_net_contribution(frm);
				},
				null,
				'success',
			);
		}
	},

	// Calculate fields when allocated_amount changes
	'references.allocated_amount': function (frm, cdt, cdn) {
		calculate_reference_row_fields(frm, cdt, cdn);
	},

	// Calculate fields when reference changes
	'references.reference_name': function (frm, cdt, cdn) {
		calculate_reference_row_fields(frm, cdt, cdn);
	},

	// Recalculate all when deductions change
	'deductions.amount': function (frm, cdt, cdn) {
		// Use setTimeout to ensure the value is updated in the model
		setTimeout(() => {
			calculate_reference_fields(frm);
		}, 200);
	},
});

// Handle deductions table events separately
frappe.ui.form.on('Payment Entry Deduction', {
	// Recalculate when deduction amount changes
	amount: function (frm, cdt, cdn) {
		setTimeout(() => {
			calculate_reference_fields(frm);
		}, 200);
	},

	// Recalculate when deduction row is added
	deductions_add: function (frm) {
		setTimeout(() => {
			calculate_reference_fields(frm);
		}, 200);
	},

	// Recalculate when deduction row is removed
	deductions_remove: function (frm) {
		setTimeout(() => {
			calculate_reference_fields(frm);
		}, 200);
	},
});

// Calculate custom fields for all reference rows
function calculate_reference_fields(frm) {
	if (!frm.doc.references || frm.doc.references.length === 0) {
		return;
	}

	// Get total deductions - ensure we access the current doc state
	let total_deductions = 0;
	if (frm.doc.deductions && frm.doc.deductions.length > 0) {
		total_deductions = frm.doc.deductions.reduce((sum, row) => {
			let amount = flt(row.amount) || 0;
			return sum + amount;
		}, 0);
	}

	// Get total allocated amount
	let total_allocated = frm.doc.references.reduce((sum, row) => {
		return sum + (flt(row.allocated_amount) || 0);
	}, 0);

	// Group references by invoice
	let invoice_groups = {};
	frm.doc.references.forEach((row) => {
		if (row.reference_doctype === 'Sales Invoice' && row.reference_name) {
			if (!invoice_groups[row.reference_name]) {
				invoice_groups[row.reference_name] = [];
			}
			invoice_groups[row.reference_name].push(row);
		}
	});

	// Calculate for each invoice group
	Object.keys(invoice_groups).forEach((invoice_name) => {
		let rows = invoice_groups[invoice_name];
		let invoice_allocated = rows.reduce((sum, row) => {
			return sum + (flt(row.allocated_amount) || 0);
		}, 0);

		// Calculate deduction for this invoice (proportional)
		let invoice_deduction = 0;
		if (total_allocated > 0) {
			invoice_deduction = (invoice_allocated / total_allocated) * total_deductions;
		}

		// Fetch invoice data and calculate for each row
		frappe.db
			.get_doc('Sales Invoice', invoice_name)
			.then((invoice) => {
				rows.forEach((row) => {
					calculate_single_reference_row(
						frm,
						row,
						invoice,
						invoice_deduction,
						invoice_allocated,
					);
				});
				frm.refresh_field('references');
			})
			.catch(() => {
				// If invoice not found, still calculate with available data
				rows.forEach((row) => {
					calculate_single_reference_row(
						frm,
						row,
						null,
						invoice_deduction,
						invoice_allocated,
					);
				});
				frm.refresh_field('references');
			});
	});
}

// Calculate fields for a single reference row
function calculate_reference_row_fields(frm, cdt, cdn) {
	let row = locals[cdt][cdn];
	if (!row || row.reference_doctype !== 'Sales Invoice' || !row.reference_name) {
		return;
	}

	// Get total deductions - ensure we access the current doc state
	let total_deductions = 0;
	if (frm.doc.deductions && frm.doc.deductions.length > 0) {
		total_deductions = frm.doc.deductions.reduce((sum, d) => {
			let amount = flt(d.amount) || 0;
			return sum + amount;
		}, 0);
	}

	// Get total allocated amount
	let total_allocated = frm.doc.references.reduce((sum, r) => {
		return sum + (flt(r.allocated_amount) || 0);
	}, 0);

	// Get invoice allocated amount
	let invoice_allocated = frm.doc.references
		.filter(
			(r) =>
				r.reference_doctype === 'Sales Invoice' && r.reference_name === row.reference_name,
		)
		.reduce((sum, r) => sum + (flt(r.allocated_amount) || 0), 0);

	// Calculate deduction for this invoice
	let invoice_deduction = 0;
	if (total_allocated > 0) {
		invoice_deduction = (invoice_allocated / total_allocated) * total_deductions;
	}

	// Fetch invoice and calculate
	frappe.db
		.get_doc('Sales Invoice', row.reference_name)
		.then((invoice) => {
			calculate_single_reference_row(
				frm,
				row,
				invoice,
				invoice_deduction,
				invoice_allocated,
			);
			frm.refresh_field('references');
		})
		.catch(() => {
			calculate_single_reference_row(frm, row, null, invoice_deduction, invoice_allocated);
			frm.refresh_field('references');
		});
}

// Calculate fields for a single row
function calculate_single_reference_row(frm, row, invoice, invoice_deduction, invoice_allocated) {
	let allocated_amount = flt(row.allocated_amount) || 0;

	// Calculate proportional deduction for this row
	let row_deduction = 0;
	if (invoice_allocated > 0) {
		row_deduction = (allocated_amount / invoice_allocated) * invoice_deduction;
	}

	// Calculate tax amount
	let tax_amount = 0;
	if (invoice && invoice.grand_total > 0) {
		let tax_ratio = (flt(invoice.total_taxes_and_charges) || 0) / invoice.grand_total;
		tax_amount = allocated_amount * tax_ratio;
	}

	// Calculate custom fields
	row.custom_tax_amount_from_allocated = flt(tax_amount, 2);
	row.custom_net_without_tax = flt(allocated_amount - tax_amount, 2);
	row.custom_net_without_tax_without_deductions = flt(
		allocated_amount - tax_amount - row_deduction,
		2,
	);
}

function calculate_net_contribution(frm) {
	// Show loading indicator
	frappe.show_alert({
		message: __('Calculating net contribution...'),
		indicator: 'blue',
	});

	// Call server method
	frappe.call({
		method: 'sales_person_net_contribution.sales_person_net_contribution.payment_entry.calculate_net_contribution',
		args: {
			payment_entry_name: frm.doc.name,
		},
		callback: function (r) {
			if (r.message) {
				if (r.message.status === 'success') {
					// Show success message (already formatted from server)
					let message = r.message.message;

					frappe.msgprint({
						title: __('Success'),
						message: message,
						indicator: 'green',
					});

					// Reload the form to show updated values
					frm.reload_doc();
				} else {
					frappe.msgprint({
						title: __('Error'),
						message: r.message.message || __('An error occurred'),
						indicator: 'red',
					});
				}
			}
		},
		error: function (r) {
			frappe.msgprint({
				title: __('Error'),
				message: r.message || __('An error occurred while calculating net contribution'),
				indicator: 'red',
			});
		},
	});
}
