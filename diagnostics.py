import sys
import os
from pprint import pprint
project_root = os.path.dirname(os.path.abspath(__file__))
print('Project root:', project_root)
sys.path.insert(0, project_root)
errors = []

# 1. Syntax check via compileall
import compileall
print('\nRunning compileall...')
res = compileall.compile_dir(project_root, force=True, quiet=1)
print('compileall result:', res)

# 2. Import modules
modules = [
    'app','utils','train_model','weather_service','market_service',
    'soil_analysis','risk_engine','report_generator','config'
]
for m in modules:
    try:
        __import__(m)
        print(f'Imported {m} OK')
    except Exception as e:
        print(f'ERROR importing {m}:', e)
        errors.append((m,str(e)))

# 3. Verify data files
files = ['crop_model.pkl','crop_recommendation_sample.csv','crop_economics.csv']
for f in files:
    p = os.path.join(project_root,f)
    print(f'{f}:', 'FOUND' if os.path.exists(p) else 'MISSING')
    if not os.path.exists(p):
        errors.append((f,'missing'))

# 4. Check CSV columns
import pandas as pd
csv_path = os.path.join(project_root,'crop_recommendation_sample.csv')
if os.path.exists(csv_path):
    try:
        df = pd.read_csv(csv_path)
        print('Training CSV columns:', df.columns.tolist()[:20])
        required = ['N','P','K','temperature','humidity','ph','rainfall','label']
        missing = [c for c in required if c not in df.columns]
        if missing:
            print('Missing training columns:', missing)
            errors.append(('csv_columns',missing))
    except Exception as e:
        print('Failed reading training CSV:', e)
        errors.append(('csv_read',str(e)))

# 5. Load model and test prediction
import joblib
model_path = os.path.join(project_root,'crop_model.pkl')
if os.path.exists(model_path):
    try:
        model = joblib.load(model_path)
        print('Loaded model:', type(model))
        # feature check: expect 7
        try:
            n_features = getattr(model, 'n_features_in_', None)
            print('model.n_features_in_ =', n_features)
            if n_features not in (7,None):
                print('Warning: model.n_features_in_ != 7')
        except Exception as e:
            print('Could not read n_features_in_:', e)
        # run a sample prediction
        import numpy as np
        X = np.array([[90,40,40,25.0,70.0,6.5,100.0]])
        try:
            pred = model.predict(X)
            proba = model.predict_proba(X)
            print('predict OK:', pred)
            print('predict_proba OK:', proba[0][:5])
        except Exception as e:
            print('Prediction failed:', e)
            errors.append(('model_predict',str(e)))
    except Exception as e:
        print('Failed to load model:', e)
        errors.append(('model_load',str(e)))

# 6. Test helper services
try:
    from weather_service import get_coordinates, get_current_weather, get_weather_forecast
    print('weather_service functions OK')
    # Try geocoding (network may be required)
    try:
        coord = get_coordinates('New Delhi, India')
        print('Geocode example:', coord)
    except Exception as e:
        print('Geocode call failed (network?):', e)
except Exception as e:
    print('weather_service import error:', e)
    errors.append(('weather_service',str(e)))

try:
    from market_service import get_market_price_for_crop, MarketDataStatus, debug_market_api
    print('market_service functions OK')
    debug_market_api('Rice')
    price, status = get_market_price_for_crop('Rice', None)
    print('market price example:', price, status)
except Exception as e:
    print('market_service error:', e)
    errors.append(('market_service',str(e)))

try:
    from soil_analysis import analyze_soil
    print('soil_analysis OK', analyze_soil(90,40,40,6.5))
except Exception as e:
    print('soil_analysis error:', e)
    errors.append(('soil_analysis',str(e)))

try:
    from risk_engine import compute_risk
    print('risk_engine OK', compute_risk('Rice', {'score':80,'details':['Nitrogen adequate']}, {'temperature':25,'rainfall':10}, {'profit':1000,'cost':20000,'season_valid':True}))
except Exception as e:
    print('risk_engine error:', e)
    errors.append(('risk_engine',str(e)))

try:
    from report_generator import build_report
    print('report_generator OK')
    rpt = build_report({'display_name':'Test'}, {'temperature':25}, {'score':80,'details':['OK']}, {'crop':'Rice'}, [{'crop':'Rice'}])
    print('report size bytes:', len(rpt))
except Exception as e:
    print('report_generator error:', e)
    errors.append(('report_generator',str(e)))

# Final summary
print('\nErrors collected:', errors)
if errors:
    sys.exit(2)
print('\nDIAGNOSTICS OK')
