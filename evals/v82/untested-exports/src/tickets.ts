export type Ticket = { id: number; open: boolean };

export function createTicket(id: number): Ticket {
  return { id, open: true };
}

export function closeTicket(t: Ticket): Ticket {
  return { ...t, open: false };
}

export async function reopenTicket(t: Ticket): Promise<Ticket> {
  return { ...t, open: true };
}
