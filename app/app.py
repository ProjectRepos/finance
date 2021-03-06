import os
import csv
from flask import Flask, request, redirect, url_for, send_from_directory, render_template, session, flash
from werkzeug.utils import secure_filename
# from flask.ext.pymongo import PyMongo
from flask_pymongo import PyMongo
from models import category_selector, loaders
from forms import forms
import logging
import datetime
import json
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s')

app = Flask(__name__)
app.config.from_pyfile('config.py')
db_finance = PyMongo(app)
db_config = PyMongo(app, config_prefix='MONGO2')

@app.route('/', methods=['GET', 'POST'])
@app.route('/home', methods=['GET', 'POST'])
def home():
    welcome_message=None
    #if new user display welcome message
    if db_finance.db.master.find_one()==None:
        welcome_message = 'new'

    #get config data
    logging.info('refreshing categorys and config')
    session['categorys'] = category_selector.get_categorys(db_config.db.categories)
    session['config_data'] = category_selector.get_config(db_config.db.cs_config)
    return render_template('home.html', welcome_message=welcome_message)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = forms.LoginForm()
    if request.method == 'POST' and form.validate():
        flash('Welcome back {0}, you have logged in successfully'.format(form.username.data), 'success')
        return redirect(url_for('home'))
    return render_template('login.html', form=form, title='login')

@app.route('/configuration_cs', methods=['GET', 'POST'])
def configuration_cs():
    updated = ''
    form = forms.ConfigForm()
    if request.method == 'POST' and form.validate():
        category_selector.update_config(db_config.db.cs_config,{
                    "SIMILARITY_THRESHOLD": float(form.SIMILARITY_THRESHOLD.data)})
        session['config_data'] = category_selector.get_config(db_config.db.cs_config)
        flash('Configuration updated successfully', 'success')

    config_data = session.get('config_data', category_selector.get_config(db_config.db.cs_config))
    form.SIMILARITY_THRESHOLD.data = str(config_data['SIMILARITY_THRESHOLD'])
    return render_template('config.html', form=form, title='Configuration')

@app.route('/current_transactions', methods=['GET', 'POST'])
def current_transactions():
    if request.method == "POST":
        if request.form.get('button', None) == 'clear':
            logging.info('clear transactions')
            db_finance.db.current_transactions.delete_many({})
            flash('Transactions cleared from cache', 'success')
            return redirect(url_for('home'))

        if request.form.get('button', None) == 'commit':
            logging.info('commited transactions')
            fieldnames = ["date","account","ammount","comment","payee","category"]
            transactions_filtered = loaders.filter_dicts([x for x in db_finance.db.current_transactions.find({})], fieldnames)
            for transaction in transactions_filtered:
                try:
                    db_finance.db.processedtransactions.insert_one(transaction)
                except:
                    flash('One transaction could not be commited as it was a duplicate', 'danger')
            flash('Transactions commited to database (master)', 'success')
            return redirect(url_for('current_transactions'))

        if request.form.get('button', None) == 'export':
            logging.info('export transactions')
            fname ='output_'+ str(datetime.date.today()) +'.csv'
            with open(os.path.join(app.config['UPLOAD_FOLDER'], fname), 'w') as csvfile:
                fieldnames = ["date","account","ammount","comment","payee","category"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(loaders.filter_dicts([x for x in db_finance.db.current_transactions.find({})], fieldnames))

            return redirect(url_for('uploaded_file', filename=fname))
            flash('File saved successfully', 'success')
            return redirect(url_for('current_transactions'))


    if db_finance.db.current_transactions.find_one({}):
        return render_template('render_data.html', data=[x for x in db_finance.db.current_transactions.find({})], page_header='Current Transactions')
    else:
        flash('You have no current stored transactions', 'danger')
        return redirect(url_for('home'))

@app.route('/stored_transactions', methods=['GET', 'POST'])
def stored_transactions():
    if request.method == "POST":
        if request.form.get('button', None) == 'clear':
            logging.info('clear transactions')
            db_finance.db.master.delete_many({})
            flash('Transactions cleared from cache', 'success')
            return redirect(url_for('home'))

        if request.form.get('button', None) == 'export':
            logging.info('export transactions')
            fname ='output_'+ str(datetime.date.today()) +'.csv'
            with open(os.path.join(app.config['UPLOAD_FOLDER'], fname), 'w') as csvfile:
                fieldnames = ["date","account","ammount","comment","payee","category"]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(loaders.filter_dicts([x for x in db_finance.db.master.find({})], fieldnames))

            return redirect(url_for('uploaded_file', filename=fname))
            flash('File saved successfully', 'success')
            return redirect(url_for('current_transactions'))


    if db_finance.db.master.find_one({}):
        return render_template('render_data.html', data=[x for x in db_finance.db.master.find({})], page_header='My Transactions')
    else:
        flash('You have no current stored transactions', 'danger')
        return redirect(url_for('home'))


@app.route('/upload_file', methods=['GET', 'POST'])
def upload_file():
    form = forms.UploadForm()
    if form.validate_on_submit() and form.dtype.data=='barclays':
        filename = secure_filename(form.file_name.data.filename)
        form.file_name.data.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return redirect(url_for('processtransactions',filename=filename))

    elif form.validate_on_submit() and form.dtype.data=='master':
        filename = secure_filename(form.file_name.data.filename)
        form.file_name.data.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        data = loaders.load_data(os.path.join(app.config['UPLOAD_FOLDER'], filename), dtype='master')
        db_finance.db.master.insert_many(data)
        logging.info('Inserting {0} transactions into master'.format(len(data)))
        return redirect(url_for('stored_transactions'))

    else:
        filename = None
    return render_template('upload.html', form=form)

@app.route('/processtransactions/<filename>', methods=['GET', 'POST'])
def processtransactions(filename):
    session['input_data'] = loaders.load_data(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    if session.get('input_data') == None or session.get('input_data') == []:
        flash("No data found in the file, please check and try again", "danger")
        return redirect(url_for('upload_file'))
    return redirect(url_for('classfication'))

@app.route('/classfication', methods=['GET', 'POST'])
def classfication():

    logging.info(' *** New Call *** ')

    form = forms.ClassficationForm()
    if request.method == 'POST':
        logging.info("Post method found")
        if request.form.get('suggestion_button', None) == 'accept_suggestion':
            ct = session.get('current_transaction')
            logging.info("Suggested category selected: {0}".format(ct['suggestion']))
            ct.update({'category':ct['suggestion']})
            db_finance.db.master.insert_one(loaders.filter_for_master(ct))
            db_finance.db.current_transactions.insert_one(ct)


        #check if any cat was SelectField
        elif form.ctype.data:
            logging.info("Examining form result from form category selected={0}".format(form.ctype.data))
            ct = session.get('current_transaction')
            ct.update({'category':form.ctype.data})
            db_finance.db.master.insert_one(loaders.filter_for_master(ct))
            db_finance.db.current_transactions.insert_one(ct)


    #get config
    logging.info('Getting config')
    cs_config = session.get('config_data', category_selector.get_config(db_config.db.cs_config))

    # Get top transaction from the input_data
    current_transactions = session.get('input_data')
    logging.info('Getting input data, len(current_transactions)={0}'.format(len(current_transactions)))
    #if there are no more transactions left redirect
    if not current_transactions or current_transactions==[]:
        logging.info('no current_transactions found finishing classfication')
        flash('Finished', 'success')
        session.clear()
        return redirect(url_for('current_transactions'))

    session['current_transaction'] = session['input_data'].pop(0)
    logging.info('current_transaction:{0}'.format(json.dumps(session['current_transaction'] )))

    #suggest_category
    current_transaction, automatic = category_selector.suggest_category(session['current_transaction'], cs_config, db_finance.db.master)

    logging.info('current_transaction after classfication:{0}'.format(json.dumps(current_transaction)))

    logging.info('adding choices for user input')
    form.ctype.choices=[]
    #set categories as form dropdown options
    for cat in session.get('categorys', category_selector.get_categorys(db_config.db.categories)):
        form.ctype.choices.append((cat, cat))

    logging.info('Rendering classfication.html to user')
    #render_template
    return render_template('classfication.html',
                            already_classfied=[x for x in db_finance.db.current_transactions.find({})][::-1],
                            current_transaction=current_transaction,
                            form=form)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
     return send_from_directory(app.config['UPLOAD_FOLDER'],filename)

app.run(host='0.0.0.0')
