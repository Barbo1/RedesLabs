/**********************************************************************
 * file:  sr_router.c
 *
 * Descripción:
 *
 * Este archivo contiene todas las funciones que interactúan directamente
 * con la tabla de enrutamiento, así como el método de entrada principal
 * para el enrutamiento.
 *
 **********************************************************************/

#include <cstdint>
#include <stdint.h>
#include <stdio.h>
#include <assert.h>
#include <stdlib.h>
#include <string.h>

#include "sr_if.h"
#include "sr_rt.h"
#include "sr_router.h"
#include "sr_protocol.h"
#include "sr_arpcache.h"
#include "sr_utils.h"

/*---------------------------------------------------------------------
 * Method: sr_init(void)
 * Scope:  Global
 *
 * Inicializa el subsistema de enrutamiento
 *
 *---------------------------------------------------------------------*/

void sr_init(struct sr_instance* sr)
{
    assert(sr);

    /* Inicializa la caché y el hilo de limpieza de la caché */
    sr_arpcache_init(&(sr->cache));

    /* Inicializa los atributos del hilo */
    pthread_attr_init(&(sr->attr));
    pthread_attr_setdetachstate(&(sr->attr), PTHREAD_CREATE_JOINABLE);
    pthread_attr_setscope(&(sr->attr), PTHREAD_SCOPE_SYSTEM);
    pthread_attr_setscope(&(sr->attr), PTHREAD_SCOPE_SYSTEM);
    pthread_t thread;

    /* Hilo para gestionar el timeout del caché ARP */
    pthread_create(&thread, &(sr->attr), sr_arpcache_timeout, sr);

} /* -- sr_init -- */

struct sr_rt* find_longest_prefix_match (struct sr_instance* sr, uint32_t ip) {
  struct sr_rt* rt_entry = sr->routing_table;
  struct sr_rt* best_entry = NULL;
  uint32_t best_mask_len = 0;
  while (rt_entry) {
    /* Verificar si la IP coincide con esta entrada. Aplico la mascara de la entrada a la IP y a la IP de destino. */
    if ((rt_entry->dest.s_addr & rt_entry->mask.s_addr) == (ip & rt_entry->mask.s_addr)) {
      uint32_t mask_len = 0;
      uint32_t mask = ntohl(rt_entry->mask.s_addr);
      /* Cuanto mas a la izquierda esté la mascara, mas bits coinciden. */
      while (mask & 0x80000000) {
          mask_len++;
          mask <<= 1;
      }
      if (mask_len > best_mask_len) {
        best_mask_len = mask_len;
        best_entry = rt_entry;
      }
    }
    rt_entry = rt_entry->next;
  }
  return best_entry;
}

/* Envía un paquete ICMP de error */
void sr_send_icmp_error_packet(uint8_t type,
                              uint8_t code,
                              struct sr_instance *sr,
                              uint32_t ipDst,
                              uint8_t *ipPacket)
{

  struct sr_ip_hdr* ip_prev_packet = (sr_ip_hdr_t*)ipPacket;

  /* El largo de icmp contempla 'Identifier', 'Sequence Number', 'Data'. */
  int len = sizeof(sr_ethernet_hdr_t) + sizeof(sr_ip_hdr_t) + sizeof(sr_icmp_t3_hdr_t);
  uint8_t* packet = (uint8_t*)malloc(len);

  /* Lleno la parte de Ethernet. */
  struct sr_ethernet_hdr* eth_packet = (sr_ethernet_hdr_t*)packet;
  eth_packet->ether_type = htons(ethertype_ip);

  /* Busco interfaz de salida. */
  struct sr_rt* match = find_longest_prefix_match(sr, ipDst);
  if (!match) { /* si no se encontró una entrada en la tabla de enrutamiento para la IP de destino, libero el paquete y retorno */
    free(packet);
    return;
  }
  struct sr_if* match_if = sr_get_interface(sr, match->interface);
  if (!match_if) { /* si no se encontró una interfaz para la entrada de la tabla de enrutamiento, libero el paquete y retorno */
    free(packet);
    return;
  }
  /* Lleno la parte de IP. */
  struct sr_ip_hdr* ip_packet = (sr_ip_hdr_t*)(packet + sizeof (sr_ethernet_hdr_t));
  ip_packet->ip_hl = sizeof (sr_ip_hdr_t) / 4;
  ip_packet->ip_v = 4;
  ip_packet->ip_len = sizeof (sr_ip_hdr_t) + sizeof(sr_icmp_t3_hdr_t);
  ip_packet->ip_tos = 0;
  ip_packet->ip_id = 0;
  ip_packet->ip_off = 0;
  ip_packet->ip_ttl = 32;
  ip_packet->ip_p = ip_protocol_icmp;
  ip_packet->ip_src = match_if->ip;
  ip_packet->ip_dst = ipDst;
  
  /* Lleno la parte de ICMP contemplada por el cabezal. */
  struct sr_icmp_t3_hdr* icmp_packet = (sr_icmp_t3_hdr_t*)(packet + sizeof(sr_ethernet_hdr_t) + sizeof(sr_ip_hdr_t));
  icmp_packet->icmp_type = type;
  icmp_packet->icmp_code = code;
  icmp_packet->unused = 0;
  icmp_packet->next_mtu = 0;
  memcpy(icmp_packet->data, ipPacket, ICMP_DATA_SIZE);
  icmp_packet->icmp_sum = icmp3_cksum (icmp_packet, sizeof(sr_icmp_t3_hdr_t));
  
  ip_packet->ip_sum = ip_cksum(ip_packet, sizeof(sr_ip_hdr_t) + sizeof(sr_icmp_t3_hdr_t));

  printf("impresion de paquete hecho para retornar un error: ");
  print_hdr_ip((uint8_t*)ip_packet);
  print_hdr_eth((uint8_t*)eth_packet);
  print_hdr_icmp((uint8_t*)icmp_packet);

  /* Envio y elimino el paquete. */
  uint32_t ip_next_hop = match->gw.s_addr;
  memcpy(eth_packet->ether_shost, match_if->addr, ETHER_ADDR_LEN);

  struct sr_arpentry* entry = sr_arpcache_lookup(&sr->cache, ip_next_hop);
  if (entry) {
    memcpy(eth_packet->ether_dhost, entry->mac, ETHER_ADDR_LEN);
    sr_send_packet(sr, packet, len, match->interface);
  } else {
    struct sr_arpreq* req = sr_arpcache_queuereq(&sr->cache, ip_next_hop, packet, len, match_if->name);
    handle_arpreq(sr, req);
  }
  free(packet);

} /* -- sr_send_icmp_error_packet -- */


void sr_handle_ip_packet(struct sr_instance *sr,
        uint8_t *packet /* lent */,
        unsigned int len,
        uint8_t *srcAddr,
        uint8_t *destAddr,
        char *interface /* lent */,
        sr_ethernet_hdr_t *eHdr) {
  
  struct sr_ethernet_hdr* eth_packet = (sr_ethernet_hdr_t*)packet;
  struct sr_ip_hdr* ip_packet = (sr_ip_hdr_t*)(packet + sizeof (sr_ethernet_hdr_t));

  printf("*** -> It is an IP packet. Print IP header.\n");
  print_hdr_ip((uint8_t*)ip_packet);

  uint32_t src = ip_packet->ip_src;
  uint32_t dest = ip_packet->ip_dst;
  
  
  /* Sanidad del paquete entrante. Longitud minima. */
  if (len < sizeof(sr_ethernet_hdr_t) + sizeof(sr_ip_hdr_t)) {
    printf("Packet too short, dropping\n");
    return;
  }
  /* Sanidad del paquete entrante. Checksum  */
  if (ip_cksum(ip_packet, sizeof(sr_ip_hdr_t)) != 0) {
    printf("Invalid IP checksum, dropping packet\n");
    return;
  }
  /* disminuyo TTL y recalculo el checksum. */
  ip_packet->ip_ttl--;
  if (ip_packet->ip_ttl == 0) {
    sr_send_icmp_error_packet(11, 0, sr, src, (uint8_t*)ip_packet);
    return;
  }
  ip_packet->ip_sum = ip_cksum(ip_packet, sizeof(sr_ip_hdr_t));

  struct sr_if* my_interface = sr_get_interface_given_ip(sr, dest);
  struct sr_rt* rt_entry;
  if (my_interface) {
      /* Manejo ICMP echo request */
    if (ip_packet->ip_p == ip_protocol_icmp) {
      int icmp_pos = sizeof (sr_ethernet_hdr_t) + sizeof(sr_ip_hdr_t);
      struct sr_icmp_hdr* icmp_packet = (sr_icmp_hdr_t*)(packet + icmp_pos);
      if (icmp_packet->icmp_type == 8 && icmp_packet->icmp_code == 0) {
        /* creo y envio el mensaje icmp echo reply. */

        int prev_data_len = len - icmp_pos;
        /* El largo de icmp contempla 'Identifier', 'Sequence Number', 'Data'. */
        int icmp_len = sizeof(sr_icmp_hdr_t) + 4 + prev_data_len;
        int len_new = icmp_pos + icmp_len;
        uint8_t* new_packet = (uint8_t*)malloc(len_new);

        /* Lleno la parte de Ethernet. */
        struct sr_ethernet_hdr* eth_new_packet = (sr_ethernet_hdr_t*)new_packet;
        memcpy(eth_new_packet->ether_shost, my_interface->addr, ETHER_ADDR_LEN); /* el router es el que responde */
        memcpy(eth_new_packet->ether_dhost, srcAddr, ETHER_ADDR_LEN);
        eth_new_packet->ether_type = htons(ethertype_ip);

        /* Lleno la parte de IP. */
        struct sr_ip_hdr* ip_new_packet = (sr_ip_hdr_t*)(new_packet + sizeof (sr_ethernet_hdr_t));
        memcpy(ip_new_packet, ip_packet, sizeof(sr_ip_hdr_t));
        ip_new_packet->ip_src = my_interface->ip; /* es la ip del router */
        ip_new_packet->ip_dst = src; /* es la ip del cliente que envió el echo request */
        
        /* Lleno la parte de ICMP contemplada por el cabezal. */
        struct sr_icmp_hdr* icmp_new_packet = (sr_icmp_hdr_t*)(new_packet + icmp_pos);
        icmp_new_packet->icmp_type = 0;
        icmp_new_packet->icmp_code = 0;

        /* Lleno la parte de ICMP que falta para el paquete echo reply. */
        uint8_t* new_packet_icmp_comps = (uint8_t*)(new_packet + sizeof(sr_icmp_hdr_t) + icmp_pos);
        memset(new_packet_icmp_comps, 0, 4);
        memcpy(new_packet_icmp_comps + 4, new_packet + icmp_pos, prev_data_len);
        
        icmp_new_packet->icmp_sum = icmp_cksum (icmp_new_packet, icmp_len);
        ip_new_packet->ip_sum = ip_cksum(ip_new_packet, sizeof(sr_ip_hdr_t) + icmp_len);

        printf("Impresion de paquete ICMP reply: ");
        print_hdr_ip((uint8_t*)ip_new_packet);
        print_hdr_eth((uint8_t*)eth_new_packet);
        print_hdr_icmp((uint8_t*)icmp_new_packet);

        /* Envio y elimino el paquete. */
        sr_send_packet(sr, new_packet, len_new, my_interface->name);
        free(new_packet);
      }
    }
    /* Manejo TCP o UDP. */
    else if (ip_packet->ip_p == 6 || ip_packet->ip_p == 17) {
      sr_send_icmp_error_packet(3, 3, sr, src, (uint8_t*)ip_packet);
      return;
    }

  } else if ((rt_entry = find_longest_prefix_match(sr, dest))) {
    uint32_t ip_next_hop = rt_entry->gw.s_addr;
    struct sr_if* exit_inter = sr_get_interface(sr, rt_entry->interface);
    memcpy(eth_packet->ether_shost, exit_inter->addr, ETHER_ADDR_LEN);

    struct sr_arpentry* entry = sr_arpcache_lookup(&sr->cache, ip_next_hop);
    if (entry) {
      memcpy(eth_packet->ether_dhost, entry->mac, ETHER_ADDR_LEN);
      sr_send_packet(sr, packet, len, rt_entry->interface);
    } else {
      struct sr_arpreq* req = sr_arpcache_queuereq(&sr->cache, ip_next_hop, packet, len, exit_inter->name);
      handle_arpreq(sr, req);
    }

  } else {
    sr_send_icmp_error_packet(3, 0, sr, src, (uint8_t*)ip_packet);
  }
}

/* Gestiona la llegada de un paquete ARP*/
void sr_handle_arp_packet(struct sr_instance *sr,
        uint8_t *packet /* lent */,
        unsigned int len,
        uint8_t *srcAddr,
        uint8_t *destAddr,
        char *interface /* lent */,
        sr_ethernet_hdr_t *eHdr) {

  /* Imprimo el cabezal ARP */
  printf("*** -> It is an ARP packet. Print ARP header.\n");
  print_hdr_arp(packet + sizeof(sr_ethernet_hdr_t));

  struct sr_arp_hdr* arp_packet = (sr_arp_hdr_t*)(packet + sizeof(sr_ethernet_hdr_t));

  /* Obtengo interfaz asociada. */
  struct sr_if* inter = sr_get_interface(sr, interface);

  uint8_t broadcast_mac[ETHER_ADDR_LEN] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};
  if (arp_packet->ar_op == arp_op_request && 
    memcmp(arp_packet->ar_tha, broadcast_mac, ETHER_ADDR_LEN) == 0) { /* memcmp compara byte a byte no strings */
  
  /* Verifico si el ARP request es para una IP del router */
  struct sr_if* target_interface = sr_get_interface_given_ip(sr, arp_packet->ar_tip);
  if (target_interface) {
    /* Es para nosotros, responder con ARP reply */
    memcpy (arp_packet->ar_tha, arp_packet->ar_sha, ETHER_ADDR_LEN);
    arp_packet->ar_tip = arp_packet->ar_sip;
    arp_packet->ar_sip = target_interface->ip;
    memcpy (arp_packet->ar_sha, target_interface->addr, ETHER_ADDR_LEN);
    arp_packet->ar_op = arp_op_reply;

    sr_send_packet(sr, packet, len, target_interface->name);
  } 
    /* Si no es para nosotros, ignorar el ARP request */
  } else if (arp_packet->ar_op == arp_op_reply && memcmp(inter->addr, arp_packet->ar_tha, ETHER_ADDR_LEN) == 0) {
    /* ARP reply para nosotros, actualizar caché y enviar paquetes pendientes */
    struct sr_arpreq* req = sr_arpcache_insert(&sr->cache, arp_packet->ar_sha, arp_packet->ar_sip);
    if (req) {
      struct sr_packet* packets = req->packets;
      while (packets) {
        struct sr_arp_hdr* arp_packet_it = (sr_arp_hdr_t*)(packets->buf + sizeof(sr_ethernet_hdr_t));
        memcpy(arp_packet_it->ar_tha, arp_packet->ar_sha, ETHER_ADDR_LEN);
        sr_send_packet(sr, packets->buf, packets->len, packets->iface);
        packets = packets->next;
      }
      sr_arpreq_destroy(&sr->cache, req);
    }

  /* COLOQUE SU CÓDIGO AQUÍ
  
  SUGERENCIAS:
  - Verifique si se trata de un ARP request o ARP reply 
  - Si es una ARP request, antes de responder verifique si el mensaje consulta por la dirección MAC asociada a una dirección IP configurada en una interfaz del router
  - Si es una ARP reply, agregue el mapeo MAC->IP del emisor a la caché ARP y envíe los paquetes que hayan estado esperando por el ARP reply
  
  */
}

/* 
* ***** A partir de aquí no debería tener que modificar nada ****
*/

/* Envía todos los paquetes IP pendientes de una solicitud ARP */
void sr_arp_reply_send_pending_packets(struct sr_instance *sr,
                                        struct sr_arpreq *arpReq,
                                        uint8_t *dhost,
                                        uint8_t *shost,
                                        struct sr_if *iface) {

  struct sr_packet *currPacket = arpReq->packets;
  sr_ethernet_hdr_t *ethHdr;
  uint8_t *copyPacket;

  while (currPacket != NULL) {
     ethHdr = (sr_ethernet_hdr_t *) currPacket->buf;
     memcpy(ethHdr->ether_shost, shost, sizeof(uint8_t) * ETHER_ADDR_LEN);
     memcpy(ethHdr->ether_dhost, dhost, sizeof(uint8_t) * ETHER_ADDR_LEN);

     copyPacket = malloc(sizeof(uint8_t) * currPacket->len);
     memcpy(copyPacket, ethHdr, sizeof(uint8_t) * currPacket->len);

     print_hdrs(copyPacket, currPacket->len);
     sr_send_packet(sr, copyPacket, currPacket->len, iface->name);
     currPacket = currPacket->next;
  }
}

/*---------------------------------------------------------------------
 * Method: sr_handlepacket(uint8_t* p,char* interface)
 * Scope:  Global
 *
 * This method is called each time the router receives a packet on the
 * interface.  The packet buffer, the packet length and the receiving
 * interface are passed in as parameters. The packet is complete with
 * ethernet headers.
 *
 * Note: Both the packet buffer and the character's memory are handled
 * by sr_vns_comm.c that means do NOT delete either.  Make a copy of the
 * packet instead if you intend to keep it around beyond the scope of
 * the method call.
 *
 *---------------------------------------------------------------------*/

void sr_handlepacket(struct sr_instance* sr,
        uint8_t * packet/* lent */,
        unsigned int len,
        char* interface/* lent */)
{
  assert(sr);
  assert(packet);
  assert(interface);

  printf("*** -> Received packet of length %d \n",len);

  /* Obtengo direcciones MAC origen y destino */
  sr_ethernet_hdr_t *eHdr = (sr_ethernet_hdr_t *) packet;
  uint8_t *destAddr = malloc(sizeof(uint8_t) * ETHER_ADDR_LEN);
  uint8_t *srcAddr = malloc(sizeof(uint8_t) * ETHER_ADDR_LEN);
  memcpy(destAddr, eHdr->ether_dhost, sizeof(uint8_t) * ETHER_ADDR_LEN);
  memcpy(srcAddr, eHdr->ether_shost, sizeof(uint8_t) * ETHER_ADDR_LEN);
  uint16_t pktType = ntohs(eHdr->ether_type);

  if (is_packet_valid(packet, len)) {
    if (pktType == ethertype_arp) {
      sr_handle_arp_packet(sr, packet, len, srcAddr, destAddr, interface, eHdr);
    } else if (pktType == ethertype_ip) {
      sr_handle_ip_packet(sr, packet, len, srcAddr, destAddr, interface, eHdr);
    }
  }

}/* end sr_ForwardPacket */
