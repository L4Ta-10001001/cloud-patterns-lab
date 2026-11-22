# Lab 01 · Circuit Breaker Pattern with Spring Boot

## What this lab demonstrates

The Circuit Breaker pattern prevents a service from continuously calling another service when it experiences repeated failures. In this lab, a food ordering service (`pedidos`) communicates with a restaurant service (`restaurantes`) to check restaurant availability.

The restaurant service can return a normal response or simulate an HTTP 500 error. The order service uses Resilience4j to detect repeated failures and temporarily stop calls to the restaurant service.

## How it works

1. `curl.exe` sends a request to the order service on port `8081`.
2. The order service calls `GET /restaurantes/1` on port `8080`.
3. With a normal request, the restaurant service returns its information, and the circuit remains in the `CLOSED` state.
4. With `fallar=true`, the restaurant service simulates an HTTP 500 error.
5. After reaching the configured failure threshold, the circuit changes to `OPEN`. The order service stops making new calls and returns a fallback response.
6. After the waiting period, the circuit changes to `HALF_OPEN` and allows test requests to check whether the restaurant service has recovered.

The Circuit Breaker is implemented in `RestauranteService.java` using Resilience4j.

## Circuit Breaker configuration

The following values are configured in the order service:

| Property | Value |
|---|---:|
| Sliding window size | 4 calls |
| Minimum number of calls | 4 |
| Failure rate threshold | 50% |
| Wait duration in open state | 10 seconds |
| Permitted calls in half-open state | 2 |

## Run the lab on Windows

You need Java 17, Maven, and `curl.exe`.

Open three PowerShell terminals from the root of the `cloud-patterns-lab` repository.

**Terminal 1 · Start Restaurants**

```powershell
mvn -f .\01-circuit-breaker\restaurantes\pom.xml spring-boot:run
```

Wait for `Started RestaurantesApplication` and leave the terminal open.

**Terminal 2 · Start Orders**

```powershell
mvn -f .\01-circuit-breaker\pedidos\pom.xml spring-boot:run
```

Wait for `Started PedidosApplication` and leave the terminal open.

**Terminal 3 · Run the tests**

### 1. Normal request

```powershell
curl.exe -i http://localhost:8081/pedidos/1
```

This request checks restaurant availability. The expected response is `200 OK`, with the circuit in the `CLOSED` state.

### 2. Simulate four failures

```powershell
1..4 | ForEach-Object {
    curl.exe -i "http://localhost:8081/pedidos/1?fallar=true"
}
```

This command sends four requests that simulate failures in the restaurant service. The responses show the fallback mechanism and the transition of the circuit to `OPEN`.

### 3. Request while the circuit is open

```powershell
curl.exe -i http://localhost:8081/pedidos/1
```

The order service returns a fallback response without calling the restaurant service again.

### 4. Check the circuit state

```powershell
curl.exe http://localhost:8081/actuator/circuitbreakers
```

This endpoint displays the current state of the Circuit Breaker, such as `OPEN` or `HALF_OPEN`.

### 5. Check service health

```powershell
curl.exe http://localhost:8081/actuator/health
```

This endpoint provides health information, including details about the Circuit Breaker.

### 6. Test recovery

After the configured waiting period, send another request:

```powershell
curl.exe -i http://localhost:8081/pedidos/1
```

Then check the circuit state again:

```powershell
curl.exe http://localhost:8081/actuator/circuitbreakers
```

The circuit allows test requests in `HALF_OPEN`. If the permitted test requests succeed, it can return to `CLOSED`.

## Observed results

| Test | Observed result |
|---|---|
| Normal request | `200 OK`, restaurant available, `CLOSED` |
| Simulated failures | Fallback responses and transition to `OPEN` |
| Request while open | Fallback response without a new call to Restaurants |
| Actuator verification | Circuit observed in `HALF_OPEN` |
| Recovery test | Restaurant responded successfully during `HALF_OPEN` |

The tests confirmed that the Circuit Breaker detects repeated failures, stops additional calls while open, and allows test requests after the waiting period.

## Possible application in AlergoAssist

The Appointments service could use a Circuit Breaker when communicating with the Doctors service to check specialist availability.

If the Doctors service experiences repeated failures, the circuit could open temporarily and prevent additional requests. The Appointments service could then inform staff that specialist availability cannot be verified at that moment.

Once the waiting period ends, test requests could determine whether communication can resume normally.
