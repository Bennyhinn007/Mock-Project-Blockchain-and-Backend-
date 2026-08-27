const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying contracts with account:", deployer.address);

  // Deploy IdentityAndAccess
  const IdentityAndAccess = await hre.ethers.getContractFactory("IdentityAndAccess");
  const identity = await IdentityAndAccess.deploy();
  await identity.waitForDeployment();
  const identityAddress = await identity.getAddress();
  console.log("IdentityAndAccess deployed to:", identityAddress);

  // Deploy AssetRegistry with IdentityAndAccess address
  const AssetRegistry = await hre.ethers.getContractFactory("AssetRegistry");
  const assetRegistry = await AssetRegistry.deploy(identityAddress);
  await assetRegistry.waitForDeployment();
  const assetAddress = await assetRegistry.getAddress();
  console.log("AssetRegistry deployed to:", assetAddress);

  // Save addresses to a JSON file for the backend to use
  const deployment = {
    network: hre.network.name,
    identityAndAccess: identityAddress,
    assetRegistry: assetAddress,
    deployer: deployer.address,
    timestamp: new Date().toISOString()
  };

  const outDir = path.join(__dirname, "..", "deployments");
  if (!fs.existsSync(outDir)) {
    fs.mkdirSync(outDir);
  }
  fs.writeFileSync(
    path.join(outDir, "localhost.json"),
    JSON.stringify(deployment, null, 2)
  );

  console.log("\nDeployment saved to deployments/localhost.json");
  console.log("\nDone! Update your backend .env with:");
  console.log(`  IDENTITY_CONTRACT_ADDRESS=${identityAddress}`);
  console.log(`  ASSET_CONTRACT_ADDRESS=${assetAddress}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
