import asyncio
import logging
import time

try:
    import usb.core
    import usb.util
    from pixel_ring import usb_pixel_ring_v2 # Explizit den USB-Treiber laden!
    HAS_PIXEL_RING = True
except ImportError:
    HAS_PIXEL_RING = False

from base_actuator import BaseActuator

logger = logging.getLogger(__name__)

class ReSpeakerLEDActuator(BaseActuator):
    """
    Steuert die 12 RGB LEDs des ReSpeaker Mic Array v2.0 über USB.
    """
    
    def __init__(self, name: str):
        super().__init__(name)
        self.pixel_ring = None
        self._init_hardware()

    def _init_hardware(self):
        if not HAS_PIXEL_RING:
            logger.warning("pixel_ring oder pyusb fehlen! Simuliere LEDs.")
            return

        try:
            # 1. Das USB-Gerät anhand seiner Vendor/Product-ID suchen
            dev = usb.core.find(idVendor=0x2886, idProduct=0x0018)
            if not dev:
                logger.error("Konnte ReSpeaker USB-Gerät nicht finden!")
                return

            # 2. Den Ring explizit an dieses gefundene USB-Gerät binden
            self.pixel_ring = usb_pixel_ring_v2.PixelRing(dev)
            
            # 3. WICHTIG: Das überschreibt das grüne Richtungs-Blinken (VAD)!
            self.pixel_ring.change_pattern('echo')
            self.pixel_ring.set_brightness(20)
            self.pixel_ring.off()
            
            logger.info(f"⭕ ReSpeaker LEDs '{self.name}' erfolgreich über USB übernommen.")
        except Exception as e:
            logger.error(f"Konnte ReSpeaker nicht initialisieren: {e}")
            logger.error("Wahrscheinlich fehlen Rechte -> Nutze 'sudo'!")

    async def execute(self, command: dict):
        """
        Führt den LED-Befehl aus. 
        """
        pattern = command.get("pattern", "think")
        duration = command.get("duration", 3.0)

        logger.info(f"💡 [LED] Muster: {pattern.upper()} | Dauer: {duration}s")

        if self.pixel_ring:
            try:
                if pattern == "wakeup":
                    self.pixel_ring.wakeup()
                elif pattern == "listen":
                    self.pixel_ring.listen()
                elif pattern == "think":
                    self.pixel_ring.think()
                elif pattern == "speak":
                    self.pixel_ring.speak()
                elif pattern == "spin":
                    self.pixel_ring.spin()
                elif pattern == "off":
                    self.pixel_ring.off()
                else:
                    self.pixel_ring.think() 
            except Exception as e:
                logger.error(f"USB Fehler bei LED-Befehl: {e}")

        # Wenn eine Dauer angegeben ist, warte und schalte danach ab
        if duration and duration > 0:
            await asyncio.sleep(duration)
            if self.pixel_ring:
                try:
                    self.pixel_ring.off()
                except:
                    pass
            logger.info(f"💡 [LED] Aus nach {duration}s.")


# --- LOKALER TEST-BEREICH ---

async def test_respeaker():
    logging.basicConfig(level=logging.INFO)
    print("\n--- Starte ReSpeaker LED USB Test ---")
    
    led = ReSpeakerLEDActuator("Test_Ring")
    await led.start()

    print("\n1. Teste Muster: Wakeup (Aufwachen)")
    led.send_command({"pattern": "wakeup", "duration": 3})
    await asyncio.sleep(3.5)

    print("\n2. Teste Muster: Think (Denken / Kreisen)")
    led.send_command({"pattern": "think", "duration": 3})
    await asyncio.sleep(3.5)

    print("\n3. Teste Muster: Speak (Sprechen / Pulsieren)")
    led.send_command({"pattern": "speak", "duration": 3})
    await asyncio.sleep(3.5)

    await led.stop()
    print("\n✅ Test beendet.")

if __name__ == "__main__":
    asyncio.run(test_respeaker())