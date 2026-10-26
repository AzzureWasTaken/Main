"""One-off admin commands.

    python manage.py setup-aws                 Create the SES/SNS/SQS resources Mailer needs
    python manage.py verify-domain example.com Start verifying your sending domain; prints DNS records
    python manage.py domain-status example.com Check whether the domain is verified yet
    python manage.py reset-password you@x.com  Set a new password for a user (if locked out)
"""

import argparse
import getpass
import json
import sys

from app import create_app, db
from app.models import User


def _client_error_code(exc):
    return getattr(exc, "response", {}).get("Error", {}).get("Code", "")


def _aws(app):
    import boto3

    if app.config["MAIL_BACKEND"] != "ses":
        print("Note: MAIL_BACKEND is not 'ses' yet. Resources will still be created.\n")
    return boto3.session.Session(region_name=app.config["AWS_REGION"])


def setup_aws(app):
    from botocore.exceptions import ClientError

    cfg = app.config
    session = _aws(app)
    ses, sns, sqs = session.client("sesv2"), session.client("sns"), session.client("sqs")
    account_id = session.client("sts").get_caller_identity()["Account"]
    print(f"AWS account {account_id}, region {cfg['AWS_REGION']}\n")

    def step(label, fn):
        try:
            result = fn()
            print(f"  OK {label}")
            return result
        except ClientError as exc:
            if "AlreadyExists" in _client_error_code(exc):
                print(f"  OK {label} (already exists)")
                return None
            raise

    config_set = cfg["SES_CONFIGURATION_SET"]
    step(f"SES configuration set '{config_set}' (open & click tracking)",
         lambda: ses.create_configuration_set(ConfigurationSetName=config_set))

    topic_arn = sns.create_topic(Name=f"{config_set}-events")["TopicArn"]
    sns.set_topic_attributes(
        TopicArn=topic_arn,
        AttributeName="Policy",
        AttributeValue=json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {"Effect": "Allow", "Principal": {"AWS": f"arn:aws:iam::{account_id}:root"},
                 "Action": "sns:*", "Resource": topic_arn},
                {"Effect": "Allow", "Principal": {"Service": "ses.amazonaws.com"}, "Action": "sns:Publish",
                 "Resource": topic_arn, "Condition": {"StringEquals": {"AWS:SourceAccount": account_id}}},
            ],
        }),
    )
    print(f"  OK SNS topic {topic_arn}")

    queue_url = sqs.create_queue(
        QueueName=cfg["SQS_QUEUE_NAME"],
        Attributes={"MessageRetentionPeriod": "1209600", "ReceiveMessageWaitTimeSeconds": "10"},
    )["QueueUrl"]
    queue_arn = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
    sqs.set_queue_attributes(
        QueueUrl=queue_url,
        Attributes={"Policy": json.dumps({
            "Version": "2012-10-17",
            "Statement": [{"Effect": "Allow", "Principal": {"Service": "sns.amazonaws.com"},
                           "Action": "sqs:SendMessage", "Resource": queue_arn,
                           "Condition": {"ArnEquals": {"aws:SourceArn": topic_arn}}}],
        })},
    )
    print(f"  OK SQS queue {queue_arn} (keeps events for 14 days if Mailer is off)")

    sns.subscribe(TopicArn=topic_arn, Protocol="sqs", Endpoint=queue_arn,
                  Attributes={"RawMessageDelivery": "true"}, ReturnSubscriptionArn=True)
    print("  OK Topic -> queue subscription")

    step("SES event publishing (delivery, open, click, bounce, complaint, unsubscribe)",
         lambda: ses.create_configuration_set_event_destination(
             ConfigurationSetName=config_set,
             EventDestinationName="mailer-sns",
             EventDestination={
                 "Enabled": True,
                 "MatchingEventTypes": ["SEND", "REJECT", "BOUNCE", "COMPLAINT", "DELIVERY", "OPEN",
                                        "CLICK", "RENDERING_FAILURE", "DELIVERY_DELAY", "SUBSCRIPTION"],
                 "SnsDestination": {"TopicArn": topic_arn},
             },
         ))

    step(f"SES contact list '{cfg['SES_CONTACT_LIST']}' (hosted one-click unsubscribe)",
         lambda: ses.create_contact_list(
             ContactListName=cfg["SES_CONTACT_LIST"],
             Topics=[{"TopicName": cfg["SES_TOPIC"], "DisplayName": "Marketing emails",
                      "Description": "News and offers by email", "DefaultSubscriptionStatus": "OPT_IN"}],
         ))
    print("\nDone. Next: python manage.py verify-domain yourdomain.com")


def verify_domain(app, domain):
    from botocore.exceptions import ClientError

    ses = _aws(app).client("sesv2")
    region = app.config["AWS_REGION"]
    try:
        ses.create_email_identity(EmailIdentity=domain)
    except ClientError as exc:
        if "AlreadyExists" not in _client_error_code(exc):
            raise
    mail_from = f"bounce.{domain}"
    ses.put_email_identity_mail_from_attributes(
        EmailIdentity=domain, MailFromDomain=mail_from, BehaviorOnMxFailure="USE_DEFAULT_VALUE"
    )
    identity = ses.get_email_identity(EmailIdentity=domain)
    tokens = identity["DkimAttributes"].get("Tokens", [])

    print(f"\nAdd these DNS records at your domain provider for {domain}:\n")
    print(f"{'Type':<6} {'Name / Host':<50} Value")
    print("-" * 110)
    for token in tokens:
        print(f"{'CNAME':<6} {f'{token}._domainkey.{domain}':<50} {token}.dkim.amazonses.com")
    print(f"{'MX':<6} {mail_from:<50} 10 feedback-smtp.{region}.amazonses.com")
    print(f"{'TXT':<6} {mail_from:<50} \"v=spf1 include:amazonses.com ~all\"")
    print(f"{'TXT':<6} {f'_dmarc.{domain}':<50} \"v=DMARC1; p=none;\"")
    print(
        "\nSome providers want only the part before your domain in the Name field "
        f"(e.g. '_dmarc' instead of '_dmarc.{domain}').\n"
        f"DNS changes can take up to 72 hours. Check with: python manage.py domain-status {domain}"
    )


def domain_status(app, domain):
    ses = _aws(app).client("sesv2")
    identity = ses.get_email_identity(EmailIdentity=domain)
    mail_from = identity.get("MailFromAttributes", {})
    print(f"Domain verified for sending: {'yes' if identity.get('VerifiedForSendingStatus') else 'not yet'}")
    print(f"DKIM status:                 {identity['DkimAttributes'].get('Status')}")
    print(f"Custom MAIL FROM status:     {mail_from.get('MailFromDomainStatus', 'not set')}")
    account = ses.get_account()
    print(f"Production access:           {'yes' if account.get('ProductionAccessEnabled') else 'NO - still in sandbox (see README)'}")


def reset_password(app, email):
    with app.app_context():
        user = User.query.filter_by(email=email.lower()).first()
        if not user:
            sys.exit(f"No user with email {email}")
        password = getpass.getpass("New password (min 10 characters): ")
        if len(password) < 10:
            sys.exit("Too short.")
        user.set_password(password)
        db.session.commit()
        print(f"Password updated for {user.name}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup-aws")
    for name in ("verify-domain", "domain-status"):
        sub.add_parser(name).add_argument("domain")
    sub.add_parser("reset-password").add_argument("email")
    args = parser.parse_args()

    app = create_app()
    if args.command == "setup-aws":
        setup_aws(app)
    elif args.command == "verify-domain":
        verify_domain(app, args.domain.lower())
    elif args.command == "domain-status":
        domain_status(app, args.domain.lower())
    elif args.command == "reset-password":
        reset_password(app, args.email)


if __name__ == "__main__":
    main()
