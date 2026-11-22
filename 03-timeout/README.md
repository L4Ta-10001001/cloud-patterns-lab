# Lab 03 · Timeout Pattern with Spring Boot

## What this lab demonstrates

When one service calls another, a timeout limits how long it waits for a response. In this lab, an order service (`pedidos`) asks an inventory service (`inventario`) how many keyboards are in stock. The inventory service can respond immediately or simulate a five-second delay. The order service has a two-second read timeout.

## How it works

1. `curl.exe` sends a request to the order service on port `8081`.
2. The order service calls `GET /inventario/1` on port `8080` and forwards the `lento` parameter.
3. With a normal request, Inventory returns a keyboard with 12 units in stock, and Orders returns `200 OK`.
4. With `lento=true`, Inventory waits five seconds before responding. Orders reaches its two-second read timeout first and returns `504 Gateway Timeout`.

The timeout is configured in the HTTP client in `PedidosController.java`. The simulated delay is implemented in `InventarioController.java`.

## Run the lab on Windows

You need Java 17, Maven, and `curl.exe`. Open three PowerShell terminals in the root of the `cloud-patterns-lab` repository.

**Terminal 1 · Start Inventory**

```powershell
mvn -f .\03-timeout\inventario\pom.xml spring-boot:run
```

Wait for `Started InventarioApplication` and leave the terminal open.

**Terminal 2 · Start Orders**

```powershell
mvn -f .\03-timeout\pedidos\pom.xml spring-boot:run
```

Wait for `Started PedidosApplication` and leave the terminal open.

**Terminal 3 · Run the three requests**

```powershell
curl.exe -sS --max-time 10 -w '\nHTTP %{http_code} - %{time_total} s\n' 'http://localhost:8081/pedidos/1'
curl.exe -sS --max-time 10 -w '\nHTTP %{http_code} - %{time_total} s\n' 'http://localhost:8081/pedidos/1?lento=true'
curl.exe -sS --max-time 10 -w '\nHTTP %{http_code} - %{time_total} s\n' 'http://localhost:8080/inventario/1?lento=true'
```

Each command prints the response body, the HTTP status, and the total time measured by `curl.exe`. The 10-second limit applies to `curl.exe`. The two-second limit applies to the call from Orders to Inventory.

## Observed results

| Request | HTTP status | Total time |
|---|---|---:|
| Normal request through Orders | `200 OK` | 0.423500 s |
| Slow request through Orders | `504 Gateway Timeout` | 2.014293 s |
| Slow request directly to Inventory | `200 OK` | 5.014461 s |

The direct request confirmed that Inventory returned the product after about five seconds. Through Orders, the same slow inventory lookup returned a timeout after about two seconds.

![PowerShell output showing the three HTTP responses and their measured times](Images/01-timeout-test.png)

## Possible application in AlergoAssist

The Appointments service could set a timeout when it calls the Doctors service to verify that a specialist is active before booking an appointment. The team could choose the timeout based on response times observed during testing.

If the verification times out, Appointments could stop the operation before saving the appointment and tell clinic staff that the specialist's information could not be verified. Staff could then try the booking again.