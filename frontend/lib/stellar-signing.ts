/**
 * Browser-only Stellar transaction signing utilities.
 * Secret keys are used exclusively here for local cryptographic signing
 * and never transmitted over the network.
 */

export async function signTransactionXdr(
  unsignedXdr: string,
  secretKey: string,
  networkPassphrase: string
): Promise<string> {
  const { Keypair, TransactionBuilder, Transaction } = await import(
    "@stellar/stellar-sdk"
  );
  const keypair = Keypair.fromSecret(secretKey);
  const parsed = TransactionBuilder.fromXDR(unsignedXdr, networkPassphrase);
  if (!(parsed instanceof Transaction)) {
    throw new Error("Expected a Transaction, got FeeBumpTransaction");
  }
  parsed.sign(keypair);
  return parsed.toEnvelope().toXDR("base64");
}

export async function publicKeyFromSecret(secretKey: string): Promise<string> {
  const { Keypair } = await import("@stellar/stellar-sdk");
  return Keypair.fromSecret(secretKey).publicKey();
}
