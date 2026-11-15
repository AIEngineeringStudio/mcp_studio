# React and MCP App flow diagrams

Quick-reference diagrams extracted from `REACT_README.md`.

## 1. React mounts the app

```text
index.html                 App.jsx
<div id="root">  <------  createRoot(...)
                                  |
                                  v
                         render(<CustomerApp />)
                                  |
                                  v
                         UI appears in the div
```

## 2. React state update and re-render cycle

```text
state changes
     |
     v
React calls component again
     |
     v
component returns new UI
     |
     v
browser updates
```

### Customer state across renders

```text
first render: customer = null  -> "Waiting for customer..."
setCustomer(data)
second render: customer = data -> customer fields appear
```

## 3. MCP event to screen update

```text
MCP Host
   |
   | tool result arrives
   v
MCP App
   |
   | event
   v
JavaScript handler
   |
   | setState(...)
   v
React re-renders
   |
   v
screen updates
```

## 4. `toolresult` listener runtime

```text
`toolresult` arrives
       |
       v
handleResult(result)
       |
       v
setState(...)
       |
       v
React re-renders
```

## 5. MCP Apps connection path

```text
MCP App UI (inside an iframe)
        |
        | MCP Apps JSON-RPC over browser postMessage
        v
MCP host
        |
        | MCP tool and resource requests
        v
MCP server
```

## 6. `useApp()` connection order

```text
useApp()
   |
   v
create App instance (new App(...))
   |
   v
configure App (below two steps are part of configuration)
   |
   +--> call onAppCreated(app)
           |
           v
        register handler/listener
           |
   +-------+
   |
   v
app.connect()
   |
   v
UI <----> host connection is ready
```

## 7. MCP Apps connection handshake

```text
1. Connect transport
       |
       v
2. UI sends ui/initialize
       |
       v
3. Host returns capabilities + context
       |
       v
4. UI sends initialized notification
       |
       v
5. App is connected
```

## 8. Host, server, and iframe topology

```text
                 MCP protocol
MCP Host  <-------------------->  MCP Server
   ^
   |
   | postMessage / MCP Apps protocol
   |
MCP App iframe
```

## 9. Tool execution to React render

```text
1. Host calls get_customer() on MCP Server

2. Server returns structuredContent

3. Host receives result

4. Host forwards toolresult event to iframe

5. React MCP App receives toolresult

6. Handler calls:
   setCustomer(result.structuredContent)

7. React re-renders
```

## 10. Safe listener registration order

```text
Create MCP App object
        |
        v
Register toolresult listener
        |
        v
Connect to host
        |
        v
Host sends toolresult
        |
        v
Listener receives it
```

## 11. Risky listener registration order

```text
Create MCP App object
        |
        v
Connect to host
        |
        v
Host sends toolresult
        |
        v
Register listener too late
```

## 12. `onAppCreated` lifecycle position

```text
useApp()
   |
   +--> creates App object
   |
   +--> calls onAppCreated(app)
   |        |
   |        +--> register listener
   |
   +--> connects app to MCP host
```

## 13. `setCustomer(result.structuredContent)` end to end

```text
1. MCP server returns a tool result
2. Host receives the result
3. Host sends a toolresult event to the UI
4. The registered listener runs
5. result.structuredContent contains the customer fields
6. setCustomer(...) stores those fields in React state
7. React calls CustomerApp again
8. customer is no longer null
9. JSX reads customer.name, customer.company, and other fields
10. React updates the visible UI
```

## 14. Whole startup flow

```text
Browser loads index.html
        |
        v
App.jsx finds #root
        |
        v
React renders <CustomerApp />
        |
        v
useState(null): no customer yet
        |
        v
useApp creates the MCP App
        |
        v
onAppCreated registers toolresult
        |
        v
useApp calls app.connect()
        |
        v
UI connects to the host
        |
        v
Host sends the customer tool result
        |
        v
Listener validates structuredContent
        |
        v
setCustomer(data)
        |
        v
React re-renders and shows the customer
```
