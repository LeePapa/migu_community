# -*- coding: utf8 -*-
from bson import json_util as bjson
from flask import flash, request, Response, stream_with_context
from flask.ext.admin.base import expose
from flask.ext.admin.contrib.fileadmin import FileAdmin
from flask.ext.admin.contrib.pymongo import ModelView
from flask.ext.admin.babel import gettext
from werkzeug import secure_filename
from wanx.base.log import print_log
from wanx.base.media import Media
from wanx import app

import os
import csv
from StringIO import StringIO


class WxFileAdmin(FileAdmin):
    allowed_extensions = ('apk', 'jpg', 'gif', 'png', 'mp4', 'css',
                          'html', 'js', 'json', 'svg', 'ttf', 'pkg')
    md5_dir = ('images', 'games', 'videos')
    list_template = 'list.html'
    can_delete = False
    can_rename = False

    def _save_form_files(self, directory, path, form):
        directory = directory.replace('\\', '/')
        md5_root_path = os.path.join(app.config.get("STATIC_BASE"), path).replace('\\', '/')
        if directory == md5_root_path and path in self.md5_dir:
            _file = Media(app.config.get("STATIC_BASE"), path, form.upload.data)
            form.upload.data.filename = _file.upload_file()
        else:
            filename = os.sep.join([directory, secure_filename(form.upload.data.filename)])

            self.save_file(filename, form.upload.data)
            self.on_file_upload(directory, path, filename)

            _dir = directory.split(app.config.get("STATIC_BASE"))[-1]
            # 更新文件存储相对路径提示
            form.upload.data.filename = os.path.join(',', _dir, form.upload.data.filename)


class WxModelView(ModelView):
    """
    admin基类
    """
    Model = None
    column_default_sort = ('create_at', True)

    def scaffold_list_columns(self):
        return self.column_details_list

    def _operation_log(self, obj, action):
        log_data = dict(
            user=request.environ.get('REMOTE_USER'),
            action=action,
            model=self.Model.__name__,
            obj_id=str(obj._id),
            data=bjson.dumps(obj)
        )
        print_log('admin_operation', bjson.dumps(log_data))

    def process_form_data(self, data):
        return data

    def create_model(self, form):
        try:
            model = form.data
            model = self.process_form_data(model)
            self._on_model_change(form, model, True)
            obj = self.Model.init()
            obj.update(model)
            ret = obj.create_model()
            model['_id'] = ret
            # 记录操作日志
            obj['_id'] = ret
            self._operation_log(obj, 'create')
        except Exception as ex:
            flash(gettext('Failed to create record. %(error)s', error=str(ex)), 'error')
            return False
        else:
            self.after_model_change(form, model, True)

        return model

    def update_model(self, form, model, exclude_fields=[]):
        try:
            data = form.data
            data = self.process_form_data(data)
            model.update(data)
            self._on_model_change(form, model, False)

            pk = self.get_pk_value(model)
            obj = self.Model.get_one(pk, check_online=False)
            obj = obj.update_model({'$set': data})
            # 记录操作日志
            self._operation_log(obj, 'update')
        except Exception as ex:
            flash(gettext('Failed to update record. %(error)s', error=str(ex)), 'error')
            return False
        else:
            self.after_model_change(form, model, False)

        return True

    def delete_model(self, model):
        try:
            pk = self.get_pk_value(model)

            if not pk:
                raise ValueError('Document does not have _id')

            self.on_model_delete(model)
            obj = self.Model.get_one(pk, check_online=False)
            obj.delete_model()
            # 记录操作日志
            self._operation_log(obj, 'delete')
        except Exception as ex:
            flash(gettext('Failed to delete record. %(error)s', error=str(ex)), 'error')
            return False
        else:
            self.after_model_delete(model)

        return True

    def is_accessible(self):

        return True

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return True

    export_columns = None
    export_max_rows = 0

    # Exporting
    def _get_data_for_export(self):
        view_args = self._get_list_extra_args()

        # Map column index to column name
        sort_column = self._get_column_by_idx(view_args.sort)

        if sort_column is not None:
            sort_column = sort_column[0]

        count, query = self.get_list(view_args.page, sort_column, view_args.sort_desc,
                                     view_args.search, view_args.filters,
                                     page_size=self.export_max_rows)
        return query

    def get_export_csv(self):
        if not self.export_columns:
            self.export_columns = [column_name for column_name, _ in self._list_columns]

        io = StringIO()
        rows = csv.DictWriter(io, self.export_columns)

        data = self._get_data_for_export()

        rows.writeheader()
        for item in data:
            row = dict()
            for column in self.export_columns:
                if column not in item:
                    continue
                row.update({column: unicode(item[column]).encode("utf8")})

            # print row
            rows.writerow(row)

        io.seek(0)
        return io.getvalue()

    @expose('/export/')
    def export(self):
        import time
        filename = '%s' % (time.strftime("%Y-%m-%d_%H-%M-%S"))
        disposition = 'attachment; filename=%s.csv' % filename
        return Response(
            stream_with_context(self.get_export_csv()),
            headers={'Content-Disposition': disposition},
            mimetype='text/csv'
        )
