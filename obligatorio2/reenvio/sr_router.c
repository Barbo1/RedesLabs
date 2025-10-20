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

/* Envía un paquete ICMP de error */
void sr_send_icmp_error_packet(uint8_t type,
                              uint8_t code,
                              struct sr_instance *sr,
                              uint32_t ipDst,
                              uint8_t *ipPacket)
{
  
  /* COLOQUE AQUÍ SU CÓDIGO*/

} /* -- sr_send_icmp_error_packet -- */

struct sr_rt* find_longest_match (struct sr_instance* sr, uint32_t ip) {
  struct sr_rt* rt_entry = sr->routing_table, *best_entry = 0;
  uint32_t best = 0, match = 0;
  while (rt_entry) {
    match = rt_entry->dest.s_addr ^ (rt_entry->mask.s_addr & ip);
    if (match < best) {
      match = best;
      best_entry = rt_entry;
    };
  }
  return rt_entry;
}

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

  ip_packet->ip_ttl--;
  if (ip_packet->ip_ttl == 0) {
    sr_send_icmp_error_packet(11, 0, sr, src, (uint8_t*)ip_packet);
    return;
  }
  ip_packet->ip_sum = ip_cksum(ip_packet, sizeof(sr_ip_hdr_t));

  struct sr_if* my_interface = sr_get_interface_given_ip(sr, dest);
  struct sr_rt* rt_entry;
  if (my_interface) {
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
        memcpy(eth_new_packet->ether_shost, destAddr, ETHER_ADDR_LEN);
        memcpy(eth_new_packet->ether_dhost, srcAddr, ETHER_ADDR_LEN);
        eth_new_packet->ether_type = htons(ethertype_arp);

        /* Lleno la parte de IP. */
        struct sr_ip_hdr* ip_new_packet = (sr_ip_hdr_t*)(packet + sizeof (sr_ethernet_hdr_t));
        memcpy(ip_new_packet, ip_packet, sizeof(sr_ip_hdr_t));
        uint32_t ip_res = ip_new_packet->ip_src;
        ip_new_packet->ip_src = ip_new_packet->ip_dst;
        ip_new_packet->ip_dst = ip_res;
        ip_new_packet->ip_sum = ip_cksum(ip_new_packet, sizeof(sr_ip_hdr_t));
        
        /* Lleno la parte de ICMP contemplada por el cabezal. */
        struct sr_icmp_hdr* icmp_new_packet = (sr_ip_hdr_t*)(packet + icmp_pos);
        icmp_new_packet->icmp_type = 0;
        icmp_new_packet->icmp_code = 0;
        icmp_new_packet->icmp_sum = icmp_cksum (icmp_new_packet, icmp_len);

        /* Lleno la parte de ICMP que falta para el paquete echo reply. */
        uint8_t* new_packet_icmp_comps = (uint8_t*)(packet + sizeof(sr_icmp_hdr_t) + icmp_pos);
        memset(new_packet_icmp_comps, 0, 4);
        memcpy(new_packet_icmp_comps + 4, packet + icmp_pos, prev_data_len);

        /* Envio y elimino el paquete. */
        sr_send_packet(sr, new_packet, len_new, rt_entry->interface);
        free(new_packet);
      }
    }

  } else if ((rt_entry = find_longest_match(sr, dest))) {
    uint32_t ip_next_hop = rt_entry->gw.s_addr;
    struct sr_arpentry* entry = sr_arpcache_lookup(&sr->cache, ip_next_hop);
    struct sr_if* to_next_hop = sr_get_interface_given_ip(sr, ip_next_hop);
    if (entry) {
      memcpy(eth_packet->ether_shost, to_next_hop->addr, ETHER_ADDR_LEN);
      memcpy(eth_packet->ether_dhost, entry->mac, ETHER_ADDR_LEN);
      sr_send_packet(sr, packet, len, rt_entry->interface);
    } else {
      struct sr_arpreq* req = sr_arpcache_queuereq(&sr->cache, ip_next_hop, packet, len, to_next_hop->name);
      handle_arpreq(sr, req);
    }

  } else {
    sr_send_icmp_error_packet(3, 1, sr, src, (uint8_t*)ip_packet);
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
