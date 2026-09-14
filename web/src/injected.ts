export function getInjectedProvider(): PhantomProviderLike | null {
  const candidate = window.phantom?.solana ?? window.solana;
  if (candidate?.isPhantom || candidate?.connect) return candidate;
  return null;
}

export function toBase58(bytes: Uint8Array): string {
  const ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
  let zeros = 0;
  while (zeros < bytes.length && bytes[zeros] === 0) zeros += 1;
  const size = Math.ceil((bytes.length * 138) / 100) + 1;
  const b = new Uint8Array(size);
  let length = 0;
  for (const byte of bytes) {
    let carry = byte;
    let i = 0;
    for (let j = size - 1; (carry !== 0 || i < length) && j >= 0; j -= 1, i += 1) {
      carry += 256 * b[j];
      b[j] = carry % 58;
      carry = Math.floor(carry / 58);
    }
    length = i;
  }
  let it = size - length;
  while (it < size && b[it] === 0) it += 1;
  let out = "1".repeat(zeros);
  for (; it < size; it += 1) out += ALPHABET[b[it]];
  return out;
}

export async function signBytes(
  provider: PhantomProviderLike,
  message: string,
): Promise<Uint8Array> {
  const encoded = new TextEncoder().encode(message);
  const result = await provider.signMessage(encoded, "utf8");
  if (result instanceof Uint8Array) return result;
  return result.signature;
}
