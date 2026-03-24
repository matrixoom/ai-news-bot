"""Push job entrypoint that renders a shared dashboard report for delivery channels."""
from datetime import datetime

from ...config import Config
from ...logger import setup_logger
from ...notifiers import (
    DiscordNotifier,
    EmailNotifier,
    SlackNotifier,
    TelegramNotifier,
    WebhookNotifier,
)
from ...services import DashboardService, PushReportService


def _default_notifier_specs():
    return [
        ("email", EmailNotifier),
        ("webhook", WebhookNotifier),
        ("slack", SlackNotifier),
        ("telegram", TelegramNotifier),
        ("discord", DiscordNotifier),
    ]


def _send_notifications(report: str, subject: str, language: str, notification_methods, logger, notifier_specs=None):
    """Send the generated report to all enabled channels."""
    lang_results = {"sent": [], "failed": []}
    specs = notifier_specs or _default_notifier_specs()

    for method_name, notifier_class in specs:
        if method_name not in notification_methods:
            continue

        logger.info(f"Sending {method_name} notification for {language.upper()}...")
        notifier = notifier_class()
        kwargs = {"language": language}
        if method_name == "email":
            kwargs["subject"] = subject
        else:
            kwargs["title"] = subject

        if notifier.send(report, **kwargs):
            lang_results["sent"].append(method_name)
            logger.info(f"{method_name.capitalize()} notification sent successfully for {language.upper()}")
        else:
            lang_results["failed"].append(method_name)
            logger.warning(f"{method_name.capitalize()} notification failed for {language.upper()}")

    return lang_results


def run_push_job(
    *,
    config: Config | None = None,
    dashboard_service: DashboardService | None = None,
    report_service: PushReportService | None = None,
    notifier_specs=None,
) -> int:
    """Run the shared dashboard push workflow through the jobs layer."""
    logger = setup_logger("ai_news_bot")

    try:
        config = config or Config()
        logger = setup_logger(
            "ai_news_bot",
            level=config.log_level,
            log_format=config.log_format,
        )
        dashboard_service = dashboard_service or DashboardService(prefer_live_data=True)
        report_service = report_service or PushReportService()

        languages = config.ai_response_languages
        notification_methods = config.notification_methods

        logger.info("=" * 60)
        logger.info("AI News Bot Push Job Starting")
        logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Languages: {', '.join(languages)}")
        logger.info("=" * 60)

        snapshot = dashboard_service.build_snapshot(force_refresh=True)
        overall_results = {"sent": [], "failed": []}

        for language in languages:
            logger.info("=" * 60)
            logger.info(f"Processing language: {language.upper()}")
            logger.info("=" * 60)

            try:
                subject = report_service.build_subject(snapshot, language=language)
                report = report_service.build_markdown(snapshot, language=language)

                logger.info(f"Dashboard report generated for {language.upper()} ({len(report)} characters)")
                preview = report[:500] + "..." if len(report) > 500 else report
                logger.info("-" * 60)
                logger.info(f"Dashboard Report Preview ({language.upper()}):")
                logger.info("-" * 60)
                logger.info(preview)
                logger.info("-" * 60)

                lang_results = _send_notifications(
                    report=report,
                    subject=subject,
                    language=language,
                    notification_methods=notification_methods,
                    logger=logger,
                    notifier_specs=notifier_specs,
                )

                for method in lang_results["sent"]:
                    result_key = f"{method} ({language.upper()})"
                    if result_key not in overall_results["sent"]:
                        overall_results["sent"].append(result_key)

                for method in lang_results["failed"]:
                    result_key = f"{method} ({language.upper()})"
                    if result_key not in overall_results["failed"]:
                        overall_results["failed"].append(result_key)

                logger.info(f"Language {language.upper()} completed successfully")

            except Exception as lang_error:
                logger.error(f"Error processing language {language.upper()}: {str(lang_error)}", exc_info=True)
                for method in notification_methods:
                    result_key = f"{method} ({language.upper()})"
                    if result_key not in overall_results["failed"]:
                        overall_results["failed"].append(result_key)

        logger.info("=" * 60)
        logger.info("AI News Bot Push Job Completed")
        logger.info(f"Processed {len(languages)} language(s): {', '.join(lang.upper() for lang in languages)}")
        logger.info(f"Successfully sent: {', '.join(overall_results['sent']) if overall_results['sent'] else 'None'}")
        if overall_results["failed"]:
            logger.warning(f"Failed to send: {', '.join(overall_results['failed'])}")
        logger.info("=" * 60)

        if notification_methods and not overall_results["sent"]:
            logger.error("All notifications failed")
            return 1

        return 0

    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        return 130
    except Exception as exc:
        logger.error(f"Application error: {str(exc)}", exc_info=True)
        return 1
