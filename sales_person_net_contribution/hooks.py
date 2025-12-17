app_name = "sales_person_net_contribution"
app_title = "Sales Person Net Contribution"
app_publisher = "abdopcnet@gmail.com"
app_description = "Sales Person Net Contribution"
app_email = "abdopcnet@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "sales_person_net_contribution",
# 		"logo": "/assets/sales_person_net_contribution/logo.png",
# 		"title": "Sales Person Net Contribution",
# 		"route": "/sales_person_net_contribution",
# 		"has_permission": "sales_person_net_contribution.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/sales_person_net_contribution/css/sales_person_net_contribution.css"
# app_include_js = "/assets/sales_person_net_contribution/js/sales_person_net_contribution.js"

# include js, css files in header of web template
# web_include_css = "/assets/sales_person_net_contribution/css/sales_person_net_contribution.css"
# web_include_js = "/assets/sales_person_net_contribution/js/sales_person_net_contribution.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "sales_person_net_contribution/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Payment Entry": "public/js/payment_entry.js"}
doctype_list_js = {"Payment Entry": "public/js/payment_entry_list.js"}
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "sales_person_net_contribution/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "sales_person_net_contribution.utils.jinja_methods",
# 	"filters": "sales_person_net_contribution.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "sales_person_net_contribution.install.before_install"
# after_install = "sales_person_net_contribution.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "sales_person_net_contribution.uninstall.before_uninstall"
# after_uninstall = "sales_person_net_contribution.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "sales_person_net_contribution.utils.before_app_install"
# after_app_install = "sales_person_net_contribution.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "sales_person_net_contribution.utils.before_app_uninstall"
# after_app_uninstall = "sales_person_net_contribution.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "sales_person_net_contribution.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

doc_events = {
    "Payment Entry": {
        "validate": "sales_person_net_contribution.sales_person_net_contribution.payment_entry.on_validate",
        "on_submit": "sales_person_net_contribution.sales_person_net_contribution.payment_entry.on_submit",
    }
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"sales_person_net_contribution.tasks.all"
# 	],
# 	"daily": [
# 		"sales_person_net_contribution.tasks.daily"
# 	],
# 	"hourly": [
# 		"sales_person_net_contribution.tasks.hourly"
# 	],
# 	"weekly": [
# 		"sales_person_net_contribution.tasks.weekly"
# 	],
# 	"monthly": [
# 		"sales_person_net_contribution.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "sales_person_net_contribution.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "sales_person_net_contribution.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "sales_person_net_contribution.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["sales_person_net_contribution.utils.before_request"]
# after_request = ["sales_person_net_contribution.utils.after_request"]

# Job Events
# ----------
# before_job = ["sales_person_net_contribution.utils.before_job"]
# after_job = ["sales_person_net_contribution.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"sales_person_net_contribution.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []
