# Not-co-logger

Not-co-logger is a simple Python library to help log things to stdout in a 
specific JSON format. It is inspired by the checkout-logger TypeScript 
library (https://github.com/CheckoutFinland/checkout-logger).

## How to use

This guide is short and in need of much verbosity.

LogSpan(requestId) creates a logspan object, which has error, warn, info and debug methods to log varying levels of messages. All messages have a type (for example "lambda.handler.start"), message, log group (for example technical or session), and optionally user (could be IP or user id) and meta (free form object).

All log rows are bound together by the requestId when logging them. Timestamps are automatically added.

## Levels

These are suggested guidelines for log levels:

* Error: The system has run into a fatal exception that requires attention from admins.
* Warning: Something went wrong, but admins do not need to be urgently alerted.
* Info: Normal logging.
* Debug: General developer friendly spam that is wanted in the logs for common "what the hell just happened" type of solving.



