// Payment Entry List View Script
// Add button to calculate net contribution for selected Payment Entries in batch

frappe.listview_settings['Payment Entry'] = {
	onload: function (listview) {
		// Add button to calculate net contribution for selected Payment Entries
		listview.page.add_inner_button(
			__('تحديث نسبة المندوب للفواتير المحددة'),
			function () {
				const selected = listview.get_checked_items();

				// Check if any items are selected
				if (!selected || !selected.length) {
					frappe.msgprint({
						message: __('Please select at least one Payment Entry.'),
						indicator: 'orange',
					});
					return;
				}

				// Filter only Payment Entries with payment_type = "Receive"
				const receive_payments = selected.filter(
					(item) => item.payment_type === 'Receive',
				);

				if (receive_payments.length === 0) {
					frappe.msgprint({
						message: __(
							'No Payment Entries with payment_type = "Receive" found in selection.',
						),
						indicator: 'orange',
					});
					return;
				}

				// Confirm action
				frappe.confirm(
					__('سيتم تحديث نسبة المندوب لـ {0} مستند Payment Entry. هل تريد المتابعة؟', [
						receive_payments.length,
					]),
					function () {
						// Process each Payment Entry sequentially (batch processing)
						(async function processBatch() {
							try {
								let successCount = 0;
								let errorCount = 0;
								const total = receive_payments.length;

								// Show initial progress
								frappe.show_alert({
									message: __('جارٍ معالجة {0} مستند...', [total]),
									indicator: 'blue',
								});

								// Process each Payment Entry one by one
								for (let i = 0; i < receive_payments.length; i++) {
									const payment_entry = receive_payments[i];

									// Get payment entry name - handle both object and string formats
									const payment_entry_name = payment_entry.name || payment_entry;

									if (!payment_entry_name) {
										errorCount++;
										console.error(
											'[payment_entry_list.js] Missing payment entry name:',
											payment_entry,
										);
										frappe.show_alert({
											message: __(
												'خطأ: اسم Payment Entry غير موجود في الصف {0}',
												[i + 1],
											),
											indicator: 'red',
										});
										continue;
									}

									// Log for debugging
									console.log(
										'[payment_entry_list.js] Processing:',
										payment_entry_name,
										'Item:',
										payment_entry,
									);

									try {
										// Show progress for current item
										frappe.show_alert({
											message: __('جارٍ معالجة {0} ({1}/{2})...', [
												payment_entry_name,
												i + 1,
												total,
											]),
											indicator: 'blue',
										});

										// Call server method to calculate net contribution
										await frappe.call({
											method: 'sales_person_net_contribution.sales_person_net_contribution.payment_entry.calculate_net_contribution',
											args: {
												payment_entry_name: payment_entry_name,
											},
										});

										successCount++;
										frappe.show_alert({
											message: __('تم معالجة {0} بنجاح', [
												payment_entry_name,
											]),
											indicator: 'green',
										});
									} catch (error) {
										errorCount++;

										// Extract error message from Frappe error response
										let errorMsg = __('خطأ في المعالجة');

										// Try different ways to extract error message
										if (error && error.exc) {
											try {
												const excData =
													typeof error.exc === 'string'
														? JSON.parse(error.exc)
														: error.exc;

												if (excData.exc_message) {
													errorMsg = excData.exc_message;
												} else if (excData.message) {
													errorMsg = excData.message;
												}
											} catch (e) {
												// If parsing fails, try other methods
												if (error.message) {
													errorMsg = error.message.substring(0, 150);
												}
											}
										} else if (error && error._server_messages) {
											try {
												const messages = JSON.parse(
													error._server_messages,
												);
												if (messages && messages.length > 0) {
													errorMsg = messages[0].message || messages[0];
												}
											} catch (e) {
												// Ignore parsing error
											}
										} else if (error && error.message) {
											errorMsg = error.message.substring(0, 150);
										}

										console.error(
											'[payment_entry_list.js] Error processing',
											payment_entry.name,
											error,
										);

										frappe.show_alert({
											message: __('{0}: {1}', [
												payment_entry_name,
												errorMsg,
											]),
											indicator: 'orange',
										});
									}
								}

								// Show final summary
								if (successCount > 0) {
									frappe.show_alert({
										message: __('تم معالجة {0} مستند بنجاح', [successCount]),
										indicator: 'green',
									});
								}

								if (errorCount > 0) {
									frappe.show_alert({
										message: __('فشل معالجة {0} مستند', [errorCount]),
										indicator: 'orange',
									});
								}

								// Refresh list view
								listview.refresh();
							} catch (error) {
								console.error(
									'[payment_entry_list.js] Batch processing error:',
									error,
								);
								frappe.show_alert({
									message: __('حدث خطأ أثناء معالجة المستندات'),
									indicator: 'red',
								});
							}
						})();
					},
				);
			},
			null,
			'success',
		);
	},
};
