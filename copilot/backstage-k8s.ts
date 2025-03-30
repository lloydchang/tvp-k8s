// Example Kubernetes Plugin Configuration
import { KubernetesBuilder } from '@backstage/plugin-kubernetes-backend';

const kubernetesProvider = await KubernetesBuilder.createBuilder({
  logger: env.logger,
  config: env.config,
}).build();

// Custom API Route Example
router.use('/kubernetes', 
  await kubernetesProvider.getClusterRoutes()
);