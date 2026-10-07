"""Read-only credential inventory and optional SMTP login test. Never sends mail."""
import argparse
import json
from pathlib import Path
import smtplib
import ssl
import sys
from dotenv import dotenv_values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--smtp-login', action='store_true')
    parser.add_argument('--output', default='reports/external-preflight.json')
    args = parser.parse_args()
    values = dotenv_values(Path(__file__).resolve().parents[1]/'.env')
    requirements = {'hunyuan':['TENCENT_SECRET_ID','TENCENT_SECRET_KEY'], 'glm':['GLM_API_KEY'],
                    'smtp':['SMTP_HOST','SMTP_USER','SMTP_PASSWORD'],
                    'blockchain':['BLOCKCHAIN_RPC_URL','BLOCKCHAIN_FROM_ADDRESS','BLOCKCHAIN_CHAIN_ID']}
    report = {name:{'configured':all(values.get(key) for key in keys),
                    'missing_keys':[key for key in keys if not values.get(key)], 'live_verified':False}
              for name, keys in requirements.items()}
    if args.smtp_login and report['smtp']['configured']:
        try:
            port = int(values.get('SMTP_PORT') or 465)
            if port == 465:
                server = smtplib.SMTP_SSL(values['SMTP_HOST'],port,timeout=15,context=ssl.create_default_context())
            else:
                server = smtplib.SMTP(values['SMTP_HOST'],port,timeout=15)
                server.starttls(context=ssl.create_default_context())
            with server: server.login(values['SMTP_USER'],values['SMTP_PASSWORD'])
            report['smtp']['login_verified'] = True
        except Exception as error:
            report['smtp']['login_verified'] = False
            report['smtp']['error_type'] = type(error).__name__
        report['smtp']['note'] = '仅验证连接/认证，未发送邮件；不证明实际投递成功'
    path = Path(args.output); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__ == '__main__': main()
