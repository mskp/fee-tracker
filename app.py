from flask import Flask, render_template, request, redirect, session, send_file
from flask_session import Session
import pandas as pd
import os
import glob
from inst_api import instalments_per_course
from helper import Defaulter

app = Flask(__name__)
app.secret_key = os.urandom(25)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
Session(app)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == "POST":
        VALID_EXCEL_EXTENSIONS = [".xls", ".xlsx",
                                  ".xlsm", ".xlsb", ".odf", ".ods", ".odt"]
        data = request.files.get('data')
        year = int(request.form.get('year'))
        data_extension = os.path.splitext(data.filename)[1]

        if data_extension not in VALID_EXCEL_EXTENSIONS:
            return render_template("error.html", msg="Invalid File Format")

        filename = "data.xlsx"
        data.save(os.path.join(app.static_folder, filename))
        session['filename'] = filename
        session['year'] = year
        return redirect('/')

    if "filename" in session:
        try:
            data = pd.read_excel(os.path.join(
                app.static_folder, session['filename']))
            students_data = pd.DataFrame(pd.read_excel(
                os.path.join(os.getcwd(), "students_data.xlsx")))
            df = pd.DataFrame(data).dropna()
            df["TRANSACTION"] = df["TRANSACTION"].str.replace("_", "")
            df = pd.merge(df, students_data[['MCODE', 'YEAR/SEM']])
            df.to_excel(os.path.join(app.static_folder,
                        session['filename']), index=False)
            data_table = df.to_html(
                index=False, classes="my-4 table table-striped table-dark table-bordered")
            return render_template("data.html", data_set=True, data_table=data_table)
        except Exception as e:
            print(e)
            session.pop("filename", None)
            return render_template("error.html", msg="Something went wrong")

    return render_template("data.html")


@app.route('/defaulters', methods=["GET", "POST"])
def defaulters():
    if "filename" not in session:
        return render_template("error.html", msg="No file available")

    AVAILABLE_COURSES = list(
        instalments_per_course(session['year']).keys())
    YEARS_SEMESTERS = set(tuple(v.keys())
                          for k, v in instalments_per_course(session['year']).items())
    if request.method == "POST":
        if request.form.get('course') and not request.form.get("year_sem"):
            session["course"] = request.form.get("course")
            return redirect(f"/defaulters/course/{session['course']}")

        elif request.form.get('year_sem') and not request.form.get("course"):
            session["year_sem"] = request.form.get("year_sem")
            return redirect(f"/defaulters/year_sem/{session['year_sem']}")

        elif request.form.get('course') and request.form.get('year_sem'):
            session["course"] = request.form.get("course")
            session["year_sem"] = request.form.get("year_sem")
            session["payable_instalments"] = instalments_per_course(session['year']).get(
                session["course"]).get(session["year_sem"])
            return render_template("defaulters.html",
                                   payable_instalments=session["payable_instalments"])

        if request.form.get("instalment"):
            session["instalment_number"] = int(request.form.get("instalment"))

        try:
            data = pd.read_excel(os.path.join(
                app.static_folder, session["filename"]))
            df = pd.DataFrame(data)
        except Exception as e:
            print(e)
            session.pop("filename", None)
            return render_template("error.html", msg=f"Something went wrong")

        try:
            defaulter = Defaulter(session['year'])
            final_dataframe = defaulter.find_defaulter(df, course=session["course"],
                                                       year_sem=session["year_sem"],
                                                       instalment_num=session["instalment_number"])
            final_dataframe.to_excel(os.path.join(
                app.static_folder, "defaulters.xlsx"), index=False) if not final_dataframe.empty else ""

            df_html = final_dataframe.to_html(
                index=False, classes="my-4 table table-striped table-dark table-bordered")\
                if not final_dataframe.empty else ""
            session["defaulters"] = "defaulters.xlsx"
            return render_template("defaulters.html",
                                   instalment=session["payable_instalments"][session["instalment_number"]],
                                   year_sem=session["year_sem"],
                                   course=session["course"],
                                   df_html=df_html, AVAILABLE_COURSES=AVAILABLE_COURSES,
                                   YEARS_SEMESTERS=YEARS_SEMESTERS
                                   )
        except Exception as e:
            print(e)
            return render_template("error.html", msg=f"Something went wrong")

    return render_template("defaulters.html",
                           AVAILABLE_COURSES=AVAILABLE_COURSES,
                           YEARS_SEMESTERS=YEARS_SEMESTERS)


@app.route('/defaulters/course/<course_name>')
def defaulters_by_course(course_name):
    if "filename" not in session:
        return render_template("error.html", msg="No file available")

    try:
        data = pd.read_excel(os.path.join(
            app.static_folder, session["filename"]))
        df = pd.DataFrame(data)
    except Exception as e:
        print(e)
        session.pop("filename", None)
        return render_template("error.html", msg=f"Something went wrong")

    try:
        defaulter = Defaulter(session['year'])
        final_df = defaulter.find_defaulter_by_course(df, course=course_name)
        df_html = final_df.to_html(
            index=False, classes="my-4 table table-striped table-dark table-bordered")\
            if not final_df.empty else ""
        session["defaulters"] = "defaulters.xlsx"
        final_df.to_excel(os.path.join(
            app.static_folder, "defaulters.xlsx"), index=False) if not final_df.empty else ""
        return render_template("defaulters_by_course.html", df_html=df_html, course=course_name)
    except Exception as e:
        print(e)
        return render_template("error.html", msg=f"Something went wrong")


@app.route('/defaulters/year_sem/<year_sem>')
def defaulters_by_year_sem(year_sem):
    if "filename" not in session:
        return render_template("error.html", msg="No file available")

    try:
        data = pd.read_excel(os.path.join(
            app.static_folder, session["filename"]))
        df = pd.DataFrame(data)
    except Exception as e:
        print(e)
        session.pop("filename", None)
        return render_template("error.html", msg=f"Something went wrong")

    try:
        defaulter = Defaulter(session['year'])
        final_df = defaulter.find_defaulter_by_year_sem(df, year_sem=year_sem)
        df_html = final_df.to_html(
            index=False, classes="my-4 table table-striped table-dark table-bordered")\
            if not final_df.empty else ""
        session["defaulters"] = "defaulters.xlsx"
        final_df.to_excel(os.path.join(
            app.static_folder, "defaulters.xlsx"), index=False) if not final_df.empty else ""
        return render_template("defaulters_by_year-sem.html", df_html=df_html, year_sem=year_sem)
    except Exception as e:
        print(e)
        return render_template("error.html", msg=f"Something went wrong")


@app.route('/defaulters/*')
def all_defaulters():
    if "filename" not in session:
        return render_template("error.html", msg="No file available")

    data = pd.read_excel(os.path.join(app.static_folder, session["filename"]))
    df = pd.DataFrame(data)

    defaulter = Defaulter(session['year'])
    defaulters_df = defaulter.find_all_defaulters(df)

    defaulters_df.to_excel(os.path.join(app.static_folder,
                                        "all_defaulters.xlsx"), index=False)
    session["all_defaulters"] = "all_defaulters.xlsx"

    return render_template('all_defaulters.html', dfs=defaulters_df)


@app.route('/defaulters/download')
def download():
    if "filename" not in session and "defaulters" not in session:
        return render_template("error.html", msg="No file available")

    return send_file(os.path.join(app.static_folder, 'defaulters.xlsx'))


@app.route("/defaulters/download/*")
def download_all():
    if "filename" not in session and "all_defaulters" not in session:
        return render_template("error.html", msg="No file available")

    return send_file(os.path.join(app.static_folder, 'all_defaulters.xlsx'))


@app.route('/destroy')
def destroy_session():
    session.pop('filename', None)
    files = glob.glob(os.path.join(app.static_folder, '*'))
    for file in files:
        os.remove(file)
    return redirect('/')


@app.errorhandler(404)
def not_found(e): return render_template("error.html", msg=e)


if __name__ == "__main__":
    mode = "dev"
    match mode:
        case "dev":
            app.run(debug=True)
        case "prod":
            from waitress import serve
            import logging
            logger = logging.getLogger('waitress')
            logger.setLevel(logging.INFO)
            serve(app, host="0.0.0.0", port=5000)
        case _:
            print("Enter valid mode, ie. ['dev', 'prod']")
