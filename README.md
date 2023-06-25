# Not-co-logger

Not-co-logger is a simple Python library to help log things to stdout in a 
specific JSON format. It is inspired by the checkout-logger TypeScript 
library (https://github.com/CheckoutFinland/checkout-logger).

## How to use

This guide is short and in need of much verbosity.

The idea behind this library is that typically in a complex cloud environment it makes ones life much easier if apps log to stdout in a consistent JSON format. This library implements in a pretty simple form some practices that have been found useful.

LogSpan(requestId) creates a logspan object, which has error, warn, info and debug methods to log varying levels of messages. All messages have a type (for example "lambda.handler.start"), message, log group (for example technical or session), and optionally user (could be IP or user id) and meta (free form object).

A good logtype is unique or at least easily greppable. We suggest naming them hierarchically, for example 'component.module.subtask' or something like that. A logtype should be informative but not overly rigid or verbose. Message is the typical human readable part of an event. Meta should be understood as a grab bag object for any additional fields that would be considered useful for the particular log event. For example a HTTP request log event could have the requested path included in the meta object.

All log rows are bound together by the requestId when logging them. Timestamps are automatically added.

## Levels

These are suggested guidelines for log levels:

* Error: The system has run into a fatal exception that requires attention from admins.
* Warning: Something went wrong, but admins do not need to be urgently alerted.
* Info: Normal logging.
* Debug: General developer friendly spam that is wanted in the logs for common "what the hell just happened" type of solving.

## Suggested group

Here are some groups that have been found to be useful:

* request: Incoming requests
* response: Outgoing responses
* session: Events related to an active session
* technical: Events related to some technical state or issues

## ExceptionSpan

When you need to log an error but only when an exception is raised, you can use ExceptionSpan context manager:

```
    with ExceptionSpan('mylog.problem', 'Doing something fails') as log:
        do_something_that_fails()
        log.info('mylog.success', 'It worked!', 'technical')
```

If `do_something_that_fails()` fails and raises an exception, the ExceptionSpan logs an error. If the call succeeds, the optional log.info() is called. Note that ExceptionSpan does not catch the exception.


