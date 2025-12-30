# Introduction

This page describes the protocols through which the server and the kernel communicate with the client. SageMath runs on the Jupyter (formerly IPython) protocol. The **client** can be any frontend for the Sage Cell, such as a web page or an app. The **server** is a Python server that acts as a bridge between the client and the kernel. The SageMath **kernel** is a custom IPython kernel that performs the computations and returns the results to the client. A client must send messages according to this protocol and display the results from the messages returned in a manner appropriate for the user interface.

The high-level overview of the communication protocol between the client, server, and kernel is as follows:
1. Client sends an HTTP request (`POST /kernel`) to the server to request a new kernel process. The server creates a new kernel process and returns the details.
2. Client opens a WebSocket connection to the server for long-running continuous communication.
3. Whenever the client sends data to the server, the server sends data to the kernel for computation, then receives the results and returns it to the client.

Further details on the Jupyter/IPython protocol can be found in their [documentation](http://ipython.org/ipython-doc/dev/development/messaging.html).

For an in-depth example of the above, see an [example Sage Cell session](session.md).

# Protocols

There are three basic protocols over which the messages are sent: HTTP, WebSockets, and SockJS.

## HTTP

HTTP is used for simple requests to the server and starting the connection to the kernel. Because of restrictions on cross-origin `XMLHttpRequest`s in the browser, the server allows several ways of performing HTTP requests:

* A standard request, such as one sent by the JavaScript `XMLHttpRequest` object, will return the result in the normal form, usually a JSON file. The results of all of these requests will have the HTTP header `Access-Control-Allow-Origin` set to `*` to allow for [cross-origin resource sharing](https://en.wikipedia.org/wiki/Cross-origin_resource_sharing).

Where this type of request is not possible (such as in older browsers that do not support CORS), it is possible to perform equivalent requests using techniques available to all the supported browsers.

* A ``GET`` request can be performed using [JSONP](https://en.wikipedia.org/wiki/JSONP). To use JSONP for a request, add a query parameter to the URL called ``callback`` whose value is the name of the JavaScript callback function.

* A ``POST`` request can be performed in JavaScript using a form submission. The target of the form should be an `iframe` element on the page, and the callback function should be added as an event listener for messages [posted](https://developer.mozilla.org/en-US/docs/DOM/window.postMessage) from the iframe.

These methods of sending requests are encapsulated in the JavaScript function `sagecell.sendRequest`, defined in `static/embedded_sagecell.js`.

## WebSockets and SockJS

WebSockets and SockJS are used to provide a continuous two-way connection with the kernel running the computation, using the server as a proxy. Messages are sent and received over WebSockets according to the [IPython messaging specification](http://ipython.org/ipython-doc/stable/development/messaging.html).

[SockJS](https://github.com/sockjs/) is used to provide the functionality of WebSockets to browsers that do not support the WebSocket API. Because only one SockJS connection may be open on a single page at any given time, we implement a multiplexing SockJS object that can send a message to any kernel and stream that the page is connected to. Each SockJS message is prepended with `[kernel ID]/[stream name],` to tell the server where to send the message. See [here](session.md) for an example.

# API

## HTTP

### Terms of Service (GET)

    GET /tos.html

#### Response

404 error if no terms of service agreement is required.  Otherwise, the html-formatted terms of service agreement is returned.


### Start a kernel

    POST /kernel

#### Parameters

The `accepted_tos` parameter is only required if the server requires a terms of service agreement.  Make sure the user accepted the terms of service before setting the parameter to `"true"`.

```json
{
    "accepted_tos": "true"
}
```

#### Response

```json
{
    "id": "[kernel ID]",
    "ws_url": "ws://sagecell.sagemath.org/"
}
```

### Start WebSocket connection

    GET <ws_url>/kernel/<kernel_id>/iopub
    GET <ws_url>/kernel/<kernel_id>/shell

#### Query Parameters

| Component | Source | Definition | Example Value |
| :--- | :--- | :--- | :--- |
| **`ws_url`** | `POST /kernel` (Response) | The base server address. | `wss://sagecell.sagemath.org` |
| **`kernel_id`** | `POST /kernel` (Response) | UUID of the Python process running on the server. | `58b66029-af1c-4664-a6ff-c3e32271712c` |

### Start SockJS connection

    GET /sockjs

### Create a permalink

    POST /permalink

#### Parameters

**message**:
```json
{
    "header": {
        "msg_type": "execute_request"
    },
    "metadata": {},
    "content": {
        "code": "[Sage code]"
    }
}
```

#### Response

```json
{
    "query": "[uuid]",
    "zip": "[base64 zipped string]"
}
```

### Blocking web service

This URL can be used as a simplified version of the API. Instead of sending and receiving messages from the kernel, the output of the computation is sent as the response to the HTTP request. Note that this does not report the output that is written to `pyout`.

    POST /service

#### Parameters

```json
{
    "code": "[the code to be executed]",
    "stdout": "[output string]"
}
```

#### Response

```json
{
    "success": true,
    "stdout": "[output string]"
}
```

## Kernel messages

Most of the messages sent between the client and the kernel over WebSockets or SockJS are the same as described in the [IPython messaging documentation](http://ipython.org/ipython-doc/stable/development/messaging.html). The messages described here are special messages produced by the Sage Cell.

### Prepare interact

This message, received by the client over the IOPub stream, tells the client to render a set of interactive controls and prepare to receive output from those controls.

This message is an IPython `display_data` message with a field named `application/sage-interact` in the `data` field.

### Update interact

When the user moves one of the interact controls to a new value,send an IPython `execute_request` message to the kernel with the following Python code to update the interact with the new values:

```python
sys._sage_.update_interact("[interact ID]", {"var_name": var_value})
```

The second argument to this function is a dictionary that maps names of controls (all the controls for that interact, not just the ones updated) to the values of those controls.

### Display HTML

This is a `display_data` message with a field named `text/html` in the `data` field. The HTML in this message should be rendered at the appropriate place in the output.

### Display an image

This is a `display_data` message with a field named `text/image-filename` in the `data` field. The value of this field is a string with a filename such as `sage0.png`. The image referenced by this message will be located at the URL `/kernel/[kernel ID]/files/[filename]`. The client should display the image in the appropriate location in the output.

### Display Jmol applet

This is a `display_data` message with a field named `application/x-jmol` in the `data` field. The value of this field is a string with a filename such as `sage1-size500-415790282.jmol.zip`. From this filename, the client can generate the URL `/kernel/[kernel ID]/files/[filename]`, which can be passed to the Jmol Java applet to display the file.

### File created

After a kernel finishes a code execution, it sends an `execute_reply` message with a `payload` in the form 
```json
[{"new_file": []}]
```

If one or more files were created as a result of the code execution, the `new_file` list will contain those filenames. These files can be accessed at the URL `/kernel/[kernel ID]/files/[filename]`. The client should provide the user with links to these files.

# A full example

This is a very rough example of version 2 protocol. Ira’s description and full example above are likely much more complete and correct.

POST request `http://sagecell.sagemath.org/kernel`

That will return a JSON dictionary that looks like this:

```json
{
    "id": "ce20fada-f757-45e5-92fa-05e952dd9c87",
    "ws_url": "ws://sagecell.sagemath.org/"
}
```

Then open up WebSocket channels to the two URLs:

Shell channel: `<ws_url>/kernel/<kernel_id>/shell`

IOPub channel: `<ws_url>/kernel/<kernel_id>/iopub`

Then send an execute_request message on the shell channel, following the [IPython format](http://ipython.org/ipython-doc/dev/development/messaging.html).

Then listen on the IOPub channel for messages until you get a kernel status idle message, and also listen on the shell channel until you get an execute_reply message.

You’ll get a kernel dead message on the IOPub channel when the cell times out.  If you don’t have interacts, it will time out pretty much immediately.  If you do have interacts, then the timeout is something 30 or 60 seconds between each `execute_request`.

I put up a short client illustrating this at https://github.com/sagemath/sagecell/blob/master/contrib/sagecell-client/sagecell-client.py (requires the Python `websocket-client` package to be installed).

Also, we changed interact messages to be more standard IPython messages.  They are no longer `interact_prepare` messages, but instead come as `display_data` messages with a MIME type of `application/sage-interact`. 

Also, here is an example of the `/service` handler: http://jsfiddle.net/2rJ5t/1/
