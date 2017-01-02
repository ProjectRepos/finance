import os
from flask import Flask, request, redirect, url_for, send_from_directory, render_template
from werkzeug.utils import secure_filename
from models import data_manager, category_selector
from forms import forms
import logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s %(message)s')

UPLOAD_FOLDER = '/Users/chrisfuller/Dropbox/Programs/finance_v2/finance/data/uploads/'
ALLOWED_EXTENSIONS = set(['txt', 'csv'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['WTF_CSRF_ENABLED'] = True
app.config['SECRET_KEY'] = 'you-will-never-guess'

dm = data_manager.DataManager()
cs = category_selector.Category_Selector(dm)


@app.route('/users_input_required', methods=['GET', 'POST'])
def users_input_required():
    form = forms.ClassficationForm()
    if request.method == 'POST':
        # check if the post request has the file part
        ct = dm.current_transaction
        ct.update({'category':form.ctype.data})
        dm.classfied.append(ct)

    dm.get_new_transaction()
    current_transaction = dm.current_transaction

    if current_transaction:
        form.ctype.choices=[]
        for cat in ['House + Groceries', 'Other + Other', 'Leisure + Entertainment', 'House + Groceries']:
            form.ctype.choices.append((cat, cat))

        return render_template('user_classfier.html',
            form=form,
            t=current_transaction,
            awaing_classfication=dm.require_user_class,
            already_classfied=dm.classfied)
    else:
        return render_template('classfication_complete.html',data=dm.classfied)


@app.route('/classfication_complete', methods=['GET', 'POST'])
def classfication_complete():
    all_classed = dm.classfied + dm.automatic_classfied
    logging.info('{0} documents user classfied'.format(len(dm.classfied))
    logging.info('{0} documents auto classfied'.format(len(dm.automatic_classfied))
    logging.info('{0} total documents classfied'.format(len(all_classed))
    return render_template("classfication_complete.html", data=dm.classfied + dm.automatic_classfied)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/', methods=['GET', 'POST'])
@app.route('/home', methods=['GET', 'POST'])
def home():
    return render_template("home.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = forms.LoginForm()
    return render_template('login.html', form=form)

@app.route('/configuration_cs', methods=['GET', 'POST'])
def configuration_cs():
    updated = ''
    form = forms.ConfigForm()
    if request.method == 'POST' and form.validate():
        cs.update_cs_config(dm,{
                    "THRESHOLD_ACCEPT_DISTANCE": float(form.TA_distance.data),
                    "THRESHOLD_ACCEPT_LIKELYHOOD_EM":float(form.TA_likelyhood_em.data),
                    "THRESHOLD_ACCEPT_LIKELYHOOD_LD":float(form.TA_likelyhood_ld.data)
                        })
        updated='configuration updated'

    cs_config_data = cs.get_config()
    form.TA_distance.data = str(cs_config_data['THRESHOLD_ACCEPT_DISTANCE'])
    form.TA_likelyhood_em.data = str(cs_config_data['THRESHOLD_ACCEPT_LIKELYHOOD_EM'])
    form.TA_likelyhood_ld.data = str(cs_config_data['THRESHOLD_ACCEPT_LIKELYHOOD_LD'])

    return render_template('config.html', form=form, updated=updated)

@app.route('/upload_file', methods=['GET', 'POST'])
def upload_file():
    form = forms.UploadForm()
    if form.validate_on_submit():
        filename = secure_filename(form.file_name.data.filename)
        form.file_name.data.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return redirect(url_for('processtransactions',filename=filename))
    else:
        filename = None
    return render_template('upload2.html', form=form)


@app.route('/processtransactions/<filename>', methods=['GET', 'POST'])
def processtransactions(filename):
    if request.method == 'POST':
            # ddm.save_transactions_bulk(
            if dm.users_input_required == []:
                return redirect(url_for('users_input_required'))
            else:
                return redirect(url_for('classfication_complete'))


    dm.load_input_data(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    automatic_classfied, users_input_required = cs.suggest_categoies_bulk(dm.input_data)

    dm.automatic_classfied = automatic_classfied
    dm.users_input_required = users_input_required

    return render_template('data_viz.html', data=automatic_classfied)

@app.route('/current_transactions')
def current_transactions():
    return render_template('render_data.html', data=dm.load_current_transactions())



@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],filename)

app.run(debug=True)
