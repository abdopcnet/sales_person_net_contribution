// Payment Entry Client Script
// Add button to calculate net contribution and update Sales Invoice Sales Team

frappe.ui.form.on('Payment Entry', {
	refresh: function (frm) {
		// Add direct button to calculate net contribution (green button)
		if (frm.doc.docstatus === 1) {
			// Only show button for submitted documents
			frm.page.add_inner_button(
				__('Calculate Net Contribution'),
				function () {
					calculate_net_contribution(frm);
				},
				null,
				'success',
			);
		}
	},
});

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
