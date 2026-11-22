package com.ejemplo.tienda.pedidos;

import java.net.SocketTimeoutException;
import java.time.Duration;
import java.util.Map;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@RestController
public class PedidosController {

    private final RestClient inventario;

    public PedidosController(@Value("${inventario.base-url}") String inventarioBaseUrl) {
        Duration timeout = Duration.ofSeconds(2);
        var requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(timeout);
        requestFactory.setReadTimeout(timeout);
        this.inventario = RestClient.builder()
                .baseUrl(inventarioBaseUrl)
                .requestFactory(requestFactory)
                .build();
    }

    @GetMapping("/pedidos/1")
    public ResponseEntity<?> consultarPedido(@RequestParam(name = "lento", defaultValue = "false") boolean lento) {
        try {
            Producto producto = inventario.get()
                    .uri(uri -> uri.path("/inventario/1").queryParam("lento", lento).build())
                    .retrieve()
                    .body(Producto.class);
            return ResponseEntity.ok(producto);
        } catch (RestClientException error) {
            if (error.contains(SocketTimeoutException.class)) {
                return ResponseEntity.status(HttpStatus.GATEWAY_TIMEOUT)
                        .body(Map.of("mensaje", "Se agotó el tiempo de espera de 2 segundos al consultar Inventario."));
            }
            String mensaje = error instanceof ResourceAccessException
                    ? "No se pudo establecer comunicación con Inventario."
                    : "Inventario devolvió una respuesta que Pedidos no pudo procesar.";
            return ResponseEntity.status(HttpStatus.BAD_GATEWAY)
                    .body(Map.of("mensaje", mensaje));
        }
    }

    public record Producto(int id, String nombre, int cantidad) {}
}
