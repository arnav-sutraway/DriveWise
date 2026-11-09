from django.contrib import admin

# Keep aggregate storage out of the editable admin tables and query-history UI.
admin.site.index_template = "monitoring/admin_index.html"
