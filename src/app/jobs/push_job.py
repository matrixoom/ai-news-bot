"""Push job entrypoint kept compatible with the legacy main.py flow."""
from datetime import datetime

from ...config import Config
from ...logger import setup_logger
from ...news import NewsGenerator
from ...notifiers import (
    DiscordNotifier,
    EmailNotifier,
    SlackNotifier,
    TelegramNotifier,
    WebhookNotifier,
)



def _send_notifications(news_digest: str, language: str, notification_methods, logger):
    """Send the generated digest to all enabled channels."""
    lang_results = {"sent": [], "failed": []}

    notifier_specs = [
        ("email", EmailNotifier),
        ("webhook", WebhookNotifier),
        ("slack", SlackNotifier),
        ("telegram", TelegramNotifier),
        ("discord", DiscordNotifier),
    ]

    for method_name, notifier_class in notifier_specs:
        if method_name not in notification_methods:
            continue

        logger.info(f"Sending {method_name} notification for {language.upper()}...")
        notifier = notifier_class()
        if notifier.send(news_digest, language=language):
            lang_results["sent"].append(method_name)
            logger.info(f"{method_name.capitalize()} notification sent successfully for {language.upper()}")
        else:
            lang_results["failed"].append(method_name)
            logger.warning(f"{method_name.capitalize()} notification failed for {language.upper()}")

    return lang_results



def run_push_job() -> int:
    """Run the legacy push workflow through the new jobs layer."""
    logger = setup_logger("ai_news_bot")

    try:
        config = Config()
        logger = setup_logger(
            "ai_news_bot",
            level=config.log_level,
            log_format=config.log_format,
        )

        languages = config.ai_response_languages
        notification_methods = config.notification_methods

        logger.info("=" * 60)
        logger.info("AI News Bot Push Job Starting")
        logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"LLM Provider: {config.llm_provider}")
        if config.llm_model:
            logger.info(f"LLM Model: {config.llm_model}")
        logger.info(f"Languages: {', '.join(languages)}")
        logger.info(f"Web Search: {config.enable_web_search}")
        logger.info("=" * 60)

        news_gen = NewsGenerator(
            provider_name=config.llm_provider,
            api_key=config.llm_api_key,
            model=config.llm_model,
            enable_web_search=config.enable_web_search,
        )

        overall_results = {"sent": [], "failed": []}

        for language in languages:
            logger.info("=" * 60)
            logger.info(f"Processing language: {language.upper()}")
            logger.info("=" * 60)

            try:
                news_digest = news_gen.generate_news_digest_from_sources(
                    language=language,
                    max_items_per_source=config.max_items_per_source,
                    stage1_template=config.stage1_prompt_template,
                    stage2_template=config.stage2_prompt_template,
                )

                logger.info(f"News digest generated for {language.upper()} ({len(news_digest)} characters)")
                preview = news_digest[:500] + "..." if len(news_digest) > 500 else news_digest
                logger.info("-" * 60)
                logger.info(f"News Digest Preview ({language.upper()}):")
                logger.info("-" * 60)
                logger.info(preview)
                logger.info("-" * 60)

                lang_results = _send_notifications(
                    news_digest=news_digest,
                    language=language,
                    notification_methods=notification_methods,
                    logger=logger,
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
