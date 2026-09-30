import argparse,json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import execution
p=argparse.ArgumentParser();p.add_argument('--engine',required=True);p.add_argument('--backend',choices=['cpu','cuda','metal'],default='cpu');a=p.parse_args()
print(json.dumps(execution.check_engine(a.engine,a.backend),indent=2))
