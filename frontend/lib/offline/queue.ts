import type { ObservationCreate } from "../api/generated";

export type QueuedObservation = {
  id: string; identity: string; payload: ObservationCreate; idempotencyKey: string; queuedAt: string;
  state: "pending" | "failed";
};

const database = "rpm-observation-queue";
const store = "observations";

function open(identity: string): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(`${database}:${identity}`, 1);
    request.onupgradeneeded = () => request.result.createObjectStore(store, { keyPath: "id" });
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function enqueueObservation(identity: string, payload: ObservationCreate, idempotencyKey = crypto.randomUUID()): Promise<QueuedObservation> {
  const item: QueuedObservation = {
    id: crypto.randomUUID(), identity, payload, idempotencyKey,
    queuedAt: new Date().toISOString(), state: "pending",
  };
  const db = await open(identity);
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(store, "readwrite");
    tx.objectStore(store).add(item); tx.oncomplete = () => resolve(); tx.onerror = () => reject(tx.error);
  });
  db.close();
  return item;
}

export async function listQueuedObservations(identity: string): Promise<QueuedObservation[]> {
  const db = await open(identity);
  const values = await new Promise<QueuedObservation[]>((resolve, reject) => {
    const request = db.transaction(store).objectStore(store).getAll();
    request.onsuccess = () => resolve(request.result as QueuedObservation[]); request.onerror = () => reject(request.error);
  });
  db.close(); return values;
}

export async function clearQueue(identity: string): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    const request = indexedDB.deleteDatabase(`${database}:${identity}`);
    request.onsuccess = () => resolve(); request.onerror = () => reject(request.error);
  });
}

export async function replayQueuedObservations(
  identity: string,
  submit: (item: QueuedObservation) => Promise<unknown>,
): Promise<number> {
  const queued = await listQueuedObservations(identity);
  if (!queued.length) return 0;
  for (const item of queued) {
    await submit(item);
    const db = await open(identity);
    try {
      await new Promise<void>((resolve, reject) => {
        const tx = db.transaction(store, "readwrite");
        tx.objectStore(store).delete(item.id);
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error);
        tx.onabort = () => reject(tx.error ?? new Error("Queue removal aborted"));
      });
    } finally { db.close(); }
  }
  return queued.length;
}
