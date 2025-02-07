import json
import os
import random
import string
import subprocess
import sys
from datetime import datetime, timezone

import sqlparse
from app.client_manager import client_manager
from app.models.main import Connection, Shortcut, UserDetails
from app.utils.crypto import make_hash
from app.utils.decorators import database_required, database_required_new, user_authenticated
from app.utils.key_manager import key_manager
from app.utils.master_password import (
    reset_master_pass,
    set_masterpass_check_text,
    validate_master_password,
)
from app.utils.response_helpers import create_response_template, error_response
from app.views.connections import session_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.shortcuts import redirect, render

from pgmanage import settings


@login_required
def index(request):
    try:
        user_details = UserDetails.objects.get(user=request.user)
    except ObjectDoesNotExist:
        user_details = UserDetails(user=request.user)
        user_details.save()

    # Invalid session
    if not request.session.get("pgmanage_session"):
        return redirect(settings.LOGIN_REDIRECT_URL)

    session = request.session.get("pgmanage_session")
    if key_manager.get(request.user):
        session.RefreshDatabaseList()

    theme = "omnidb" if user_details.theme == "light" else "omnidb_dark"

    context = {
        "session": None,
        "editor_theme": theme,
        "theme": user_details.theme,
        "font_size": user_details.font_size,
        "user_id": request.user.id,
        "user_key": request.session.session_key,
        "user_name": request.user.username,
        "super_user": request.user.is_superuser,
        "csv_encoding": user_details.csv_encoding,
        "csv_delimiter": user_details.csv_delimiter,
        "desktop_mode": settings.DESKTOP_MODE,
        "pgmanage_version": settings.PGMANAGE_VERSION,
        "pgmanage_short_version": settings.PGMANAGE_SHORT_VERSION,
        "menu_item": "workspace",
        "tab_token": "".join(
            random.choice(string.ascii_lowercase + string.digits) for i in range(20)
        ),
        "url_folder": settings.PATH, # FIXME: rename this to base_path
        "csrf_cookie_name": settings.CSRF_COOKIE_NAME,
        "master_key": "new"
        if not bool(user_details.masterpass_check)
        else bool(key_manager.get(request.user)),
        "binary_path": user_details.get_binary_path(),
        "pigz_path": user_details.get_pigz_path(),
        "date_format": user_details.date_format,
    }

    # wiping saved tabs databases list
    session.v_tabs_databases = dict([])
    request.session["pgmanage_session"] = session

    client_manager.clear_client(client_id=request.session.session_key)

    return render(request, "app/workspace.html", context)


@user_authenticated
@session_required
def save_config_user(request, session):
    response_data = {"data": "", "status": "success"}

    data = request.data

    font_size = data["font_size"]
    theme = data["theme"]
    password = data["password"]
    csv_encoding = data["csv_encoding"]
    csv_delimiter = data["csv_delimiter"]
    binary_path = data["binary_path"]
    date_format = data["date_format"]
    pigz_path = data["pigz_path"]

    session.v_theme_id = theme
    session.v_font_size = font_size
    session.v_csv_encoding = csv_encoding
    session.v_csv_delimiter = csv_delimiter

    user_details = UserDetails.objects.get(user=request.user)
    user_details.theme = theme
    user_details.font_size = font_size
    user_details.csv_encoding = csv_encoding
    user_details.csv_delimiter = csv_delimiter
    user_details.binary_path = binary_path
    user_details.date_format = date_format
    user_details.pigz_path = pigz_path
    user_details.save()

    request.session["pgmanage_session"] = session

    if password != "":
        user = User.objects.get(id=request.user.id)
        user.set_password(password)
        user.save()
        update_session_auth_hash(request, user)

    return JsonResponse(response_data)


@user_authenticated
@session_required(include_session=False)
def shortcuts(request):
    response_data = {"data": "", "status": "success"}

    if request.method == "POST":
        data = request.data
        shortcut_list = data.get("shortcuts")
        current_os = data.get("current_os")

        try:
            # Delete existing user shortcuts
            Shortcut.objects.filter(user=request.user).delete()

            # Adding new user shortcuts
            for shortcut in shortcut_list:
                shortcut_object = Shortcut(
                    user=request.user,
                    code=shortcut["shortcut_code"],
                    os=current_os,
                    ctrl_pressed=shortcut["ctrl_pressed"],
                    shift_pressed=shortcut["shift_pressed"],
                    alt_pressed=shortcut["alt_pressed"],
                    meta_pressed=shortcut["meta_pressed"],
                    key=shortcut["shortcut_key"],
                )
                shortcut_object.save()
        except Exception as exc:
            response_data["data"] = str(exc)
            response_data["status"] = "failed"
            return JsonResponse(response_data, status=400)

    if request.method == "GET":
        data = {}

        user_shortcuts = Shortcut.objects.filter(user=request.user)
        for shortcut in user_shortcuts:
            data[shortcut.code] = {
                "ctrl_pressed": shortcut.ctrl_pressed,
                "shift_pressed": shortcut.shift_pressed,
                "alt_pressed": shortcut.alt_pressed,
                "meta_pressed": shortcut.meta_pressed,
                "shortcut_key": shortcut.key,
                "os": shortcut.os,
                "shortcut_code": shortcut.code,
            }
        response_data["data"] = data

    return JsonResponse(response_data)


@user_authenticated
@session_required
def change_active_database(request, session):
    data = request.data
    tab_id = data["tab_id"]
    new_database = data["database"]
    conn_id = data["database_index"]

    session.v_tabs_databases[tab_id] = new_database

    conn = Connection.objects.get(id=conn_id)
    conn.last_used_database = new_database
    conn.last_access_date = datetime.now(tz=timezone.utc)
    conn.save()

    request.session["pgmanage_session"] = session

    return JsonResponse(data={"data": "database changed"})


@user_authenticated
@session_required(use_old_error_format=True)
def renew_password(request, session):
    response_data = create_response_template()

    data = request.data
    database_index = data["p_database_index"]
    password = data["p_password"]

    database_object = session.v_databases[database_index]
    database_object["database"].v_connection.v_password = password

    test = database_object["database"].TestConnection()

    if test == "Connection successful.":
        database_object["prompt_timeout"] = datetime.now()
    else:
        response_data["v_error"] = True
        response_data["v_data"] = test

    request.session["pgmanage_session"] = session

    return JsonResponse(response_data)


@user_authenticated
@database_required_new(check_timeout=True, open_connection=True)
def draw_graph(request, database):
    response_data = create_response_template()
    schema = request.data.get("schema", '')
    edge_dict = {}
    node_dict = {}

    try:
        tables = database.QueryTables(False, schema)

        for table in tables.Rows:
            node_data = {
                "id": table["table_name"],
                "label": table["table_name"],
                "group": 1,
                "columns": []
            }
            table_name = table.get('name_raw') or table["table_name"]
            table_columns = database.QueryTablesFields(
                table_name, False, schema
            ).Rows

            node_data['columns'] = list(({
                'name': c['column_name'],
                'type': c['data_type'],
                'cgid': None,
                'is_pk': False,
                'is_fk': False,
                } for c in table_columns))

            node_dict[table["table_name"]] = node_data

        q_fks = database.QueryTablesForeignKeys(None, False, schema)

        for fk in q_fks.Rows:
            # ensure that the new edge stays within the same schema and points to an existing table
            # table partitions are *not* included in the node list
            # FIXME: resolve FKs of partitioned table from its partitions
            if fk["r_table_schema"] == schema and fk["table_name"] in node_dict.keys():
                edge_dict[fk["constraint_name"]] = {
                    "from": fk["table_name"],
                    "to": fk["r_table_name"],
                    "from_col": None,
                    "to_col": None,
                    "label": "",
                    "arrows": "to",
                    "cgid": None
                }

        q_fkcols = database.QueryTablesForeignKeysColumns(list(edge_dict.keys()), None, False, schema)
        for fkcol in q_fkcols.Rows:
            cgid = fkcol['constraint_name']
            edge = edge_dict[fkcol['constraint_name']]
            edge['from_col'] = fkcol['column_name']
            edge['to_col'] = fkcol['r_column_name']
            edge['cgid'] = cgid
            table = node_dict[fkcol['table_name']]
            r_table = node_dict[fkcol['r_table_name']]
            for col in table['columns']:
                if col['name'] == fkcol['column_name']:
                    col['is_fk'] = True
                    col['cgid'] = cgid

            for col in r_table['columns']:
                if col['name'] == fkcol['r_column_name']:
                    # FIXME: this is incomplete, seting PK based on FK constraints is not enough
                    # there may be unreferenced PKs which will be missed
                    col['is_pk'] = True
                    col['cgid'] = f"{fkcol['r_table_name']}-{fkcol['r_column_name']}"

        response_data["v_data"] = {"nodes": list(node_dict.values()), "edges": list(edge_dict.values())}

    except Exception as exc:
        return error_response(message=str(exc), password_timeout=True)

    return JsonResponse(response_data)


@user_authenticated
@database_required(p_check_timeout=True, p_open_connection=True)
def start_edit_data(request, v_database):
    response_data = create_response_template()
    response_data["v_data"] = {"v_pk": [], "v_cols": [], "v_ini_orderby": ""}
    data = request.data
    table = data["p_table"]

    if v_database.v_has_schema:
        schema = data["p_schema"]

    try:
        if v_database.v_has_schema:
            pk = v_database.QueryTablesPrimaryKeys(table, False, schema)
            columns = v_database.QueryTablesFields(table, False, schema)
        else:
            pk = v_database.QueryTablesPrimaryKeys(table)
            columns = v_database.QueryTablesFields(table)

        pk_cols = None
        if pk is not None and len(pk.Rows) > 0:
            if v_database.v_has_schema:
                pk_cols = v_database.QueryTablesPrimaryKeysColumns(
                    pk.Rows[0]["constraint_name"], table, False, schema
                )
            else:
                pk_cols = v_database.QueryTablesPrimaryKeysColumns(table)

            response_data["v_data"]["v_ini_orderby"] = "ORDER BY "
            first = True
            for pk_col in pk_cols.Rows:
                if not first:
                    response_data["v_data"]["v_ini_orderby"] = (
                        response_data["v_data"]["v_ini_orderby"] + ", "
                    )
                first = False
                response_data["v_data"]["v_ini_orderby"] = (
                    response_data["v_data"]["v_ini_orderby"]
                    + "t."
                    + pk_col["column_name"]
                )
        index = 0
        for column in columns.Rows:
            col = {
                "v_type": column["data_type"],
                "v_column": column["column_name"],
                "v_is_pk": False,
            }
            # Finding corresponding PK column
            if pk_cols is not None:
                for pk_col in pk_cols.Rows:
                    if pk_col["column_name"].lower() == column["column_name"].lower():
                        col["v_is_pk"] = True
                        pk_info = {
                            "v_column": pk_col["column_name"],
                            "v_index": index,
                            "v_type": column["data_type"],
                        }
                        response_data["v_data"]["v_pk"].append(pk_info)
                        break
            response_data["v_data"]["v_cols"].append(col)
            index += 1

    except Exception as exc:
        return error_response(message=str(exc), password_timeout=True)

    return JsonResponse(response_data)


@user_authenticated
@database_required_new(check_timeout=True, open_connection=True)
def get_table_columns(request, database):
    data = request.data
    table = data["table"]

    if database.v_has_schema:
        schema = data["schema"]

    try:
        if database.v_has_schema:
            pk = database.QueryTablesPrimaryKeys(table, False, schema)
            columns = database.QueryTablesFields(table, False, schema)
        else:
            pk = database.QueryTablesPrimaryKeys(table)
            columns = database.QueryTablesFields(table)

        # generate ORDER BY from table PKs
        order_by = ''
        pk_column_names = []
        if pk is not None and len(pk.Rows) > 0:
            if database.v_has_schema:
                pk_cols = database.QueryTablesPrimaryKeysColumns(
                    pk.Rows[0]["constraint_name"], table, False, schema
                )
            else:
                pk_cols = database.QueryTablesPrimaryKeysColumns(table)

            cols = ', '.join(['t.'+x['column_name'] for x in pk_cols.Rows])
            order_by = f"ORDER BY {cols}"

            pk_column_names = [x['column_name'] for x in pk_cols.Rows]

        table_columns = []
        for column in columns.Rows:
            table_columns.append({
                "data_type": column['data_type'],
                "name": column['column_name'],
                "is_primary": column['column_name'] in pk_column_names,
            })

    except Exception as exc:
        return JsonResponse(data={'data': str(exc)}, status=400)

    return JsonResponse(data={'columns': table_columns, 'initial_orderby': order_by})


@user_authenticated
@database_required(p_check_timeout=True, p_open_connection=True)
def get_completions_table(request, v_database):
    response_data = create_response_template()

    data = request.data
    table = data["p_table"]
    schema = data["p_schema"]

    if v_database.v_has_schema:
        table_name = schema + "." + table
    else:
        table_name = table

    fields_list = []

    try:
        data = v_database.v_connection.GetFields(
            "select x.* from " + table_name + " x where 1 = 0"
        )
    except Exception as exc:
        return error_response(message=str(exc), password_timeout=True)

    score = 100

    score -= 100

    for field in data:
        fields_list.append(
            {
                "value": "t." + field.v_truename,
                "score": score,
                "meta": field.v_dbtype,
            }
        )
        v_score -= 100

    response_data["v_data"] = fields_list

    return JsonResponse(response_data)


@user_authenticated
@database_required(p_check_timeout=True, p_open_connection=True)
def refresh_monitoring(request, v_database):
    response_data = create_response_template()

    sql = request.data["p_query"]

    try:
        data = v_database.Query(sql, True, True)

        response_data["v_data"] = {
            "col_names": data.Columns,
            "data": json.loads(data.Jsonify()),
        }
    except Exception as exc:
        return error_response(message=str(exc), password_timeout=True)

    return JsonResponse(response_data)


def get_alias(p_sql, p_pos, p_val):
    try:
        s = sqlparse.parse(p_sql)
        alias = p_val[:-1]
        for stmt in s:
            for item in stmt.tokens:
                if item.ttype is None:
                    try:
                        cur_alias = item.get_alias()
                        if cur_alias is None:
                            if item.value == alias:
                                return item.value
                        elif cur_alias == alias:
                            # check if there is punctuation
                            if str(item.tokens[1].ttype) != "Token.Punctuation":
                                return item.get_real_name()
                            return item.tokens[0].value + "." + item.tokens[2].value
                    except Exception:
                        pass

    except Exception:
        return
    return


@user_authenticated
@database_required(p_check_timeout=True, p_open_connection=True)
def get_autocomplete_results(request, v_database):
    response_data = create_response_template()

    data = request.data
    sql = data["p_sql"]
    value = data["p_value"]
    pos = data["p_pos"]
    num_dots = value.count(".")

    result = []
    max_result_word = ""
    max_complement_word = ""

    alias = None
    if value != "" and value[-1] == ".":
        alias = get_alias(sql, pos, value)
        if alias:
            try:
                data = v_database.v_connection.GetFields(
                    "select x.* from " + alias + " x where 1 = 0"
                )
                current_group = {"type": "column", "elements": []}
                max_result_length = 0
                max_complement_length = 0
                for v_type in data:
                    curr_result_length = len(value + v_type.v_truename)
                    curr_complement_length = len(v_type.v_dbtype)
                    curr_result_word = value + v_type.v_truename
                    curr_complement_word = v_type.v_dbtype

                    if curr_result_length > max_result_length:
                        max_result_length = curr_result_length
                        max_result_word = curr_result_word
                    if curr_complement_length > max_complement_length:
                        max_complement_length = curr_complement_length
                        max_complement_word = curr_complement_word

                    current_group["elements"].append(
                        {
                            "value": value + v_type.v_truename,
                            "select_value": value + v_type.v_truename,
                            "complement": v_type.v_dbtype,
                        }
                    )
                if len(current_group["elements"]) > 0:
                    result.append(current_group)
            except Exception:
                pass

    if not alias:
        filter_part = f"where search.result like '{value}%' "
        query_columns = "type,sequence,result,select_value,complement"
        if num_dots > 0:
            filter_part = f"where search.result_complete like '{value}%' and search.num_dots <= {num_dots}"
            query_columns = "type,sequence,result_complete as result,select_value,complement_complete as complement"
        elif value == "":
            filter_part = "where search.num_dots = 0 "

        try:
            max_result_length = 0
            max_complement_length = 0

            search = v_database.GetAutocompleteValues(query_columns, filter_part)

            if search is not None:
                current_group = {"type": "", "elements": []}
                if len(search.Rows) > 0:
                    current_group["type"] = search.Rows[0]["type"]
                for search_row in search.Rows:
                    if current_group["type"] != search_row["type"]:
                        result.append(current_group)
                        current_group = {"type": search_row["type"], "elements": []}

                    curr_result_length = len(search_row["result"])
                    curr_complement_length = len(search_row["complement"])
                    curr_result_word = search_row["result"]
                    curr_complement_word = search_row["complement"]
                    current_group["elements"].append(
                        {
                            "value": search_row["result"],
                            "select_value": search_row["select_value"],
                            "complement": search_row["complement"],
                        }
                    )

                    if curr_result_length > max_result_length:
                        max_result_length = curr_result_length
                        max_result_word = curr_result_word
                    if curr_complement_length > max_complement_length:
                        max_complement_length = curr_complement_length
                        max_complement_word = curr_complement_word

                if len(current_group["elements"]) > 0:
                    result.append(current_group)

        except Exception as exc:
            return error_response(message=str(exc), password_timeout=True)

    response_data["v_data"] = {
        "data": result,
        "max_result_word": max_result_word,
        "max_complement_word": max_complement_word,
    }

    return JsonResponse(response_data)


@user_authenticated
@session_required(use_old_error_format=True)
def master_password(request, session):
    """
    Set the master password and store in the memory
    This password will be used to encrypt/decrypt saved server passwords
    """

    response_data = create_response_template()

    data = request.data
    master_pass = data["master_password"]

    master_pass_hash = make_hash(master_pass, request.user)
    user_details = UserDetails.objects.get(user=request.user)

    # if master pass is set previously
    if user_details.masterpass_check and not validate_master_password(
        user_details, master_pass_hash
    ):
        return error_response(message="Master password is not correct.")

    if data != "" and data.get("master_password", "") != "":
        # store the master pass in the memory
        key_manager.set(request.user, master_pass_hash)

        # set the encrypted sample text with the new master pass
        set_masterpass_check_text(user_details, master_pass_hash)

    elif data.get("master_password", "") == "":
        return error_response(message="Master password cannot be empty.")

    # refreshing database session list with provided master password
    session.RefreshDatabaseList()

    # saving new pgmanage_session
    request.session["pgmanage_session"] = session

    return JsonResponse(response_data)


@user_authenticated
def reset_master_password(request):
    """
    Removes the master password and remove all saved passwords
    This password will be used to encrypt/decrypt saved server passwords
    """

    response_data = create_response_template()

    user_details = UserDetails.objects.get(user=request.user)

    reset_master_pass(user_details)

    return JsonResponse(response_data)


@user_authenticated
def validate_binary_path(request):
    data = request.data

    binary_path = data.get("binary_path")

    utilities = data.get("utilities")

    result = {}

    env = os.environ.copy()

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        env.pop("LD_LIBRARY_PATH", None)

    for utility in utilities:
        full_path = os.path.join(
            binary_path, utility if os.name != "nt" else (utility + ".exe")
        )

        if not os.path.exists(full_path):
            result[utility] = "not found on the specifed binary path."
            continue

        shell_result = subprocess.run(
            f'"{full_path}" --version',
            shell=True,
            env=env,
            capture_output=True,
            text=True,
        )

        utility_version = shell_result.stdout

        result_utility_version = utility_version.replace(utility, "").strip()

        result[utility] = result_utility_version

    return JsonResponse(data={"data": result})
