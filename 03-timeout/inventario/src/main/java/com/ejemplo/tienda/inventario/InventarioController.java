package com.ejemplo.tienda.inventario;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class InventarioController {

    @GetMapping("/inventario/1")
    public Producto consultarProducto(@RequestParam(name = "lento", defaultValue = "false") boolean lento)
            throws InterruptedException {
        if (lento) {
            Thread.sleep(5_000);
        }
        return new Producto(1, "Teclado", 12);
    }

    public record Producto(int id, String nombre, int cantidad) {}
}
