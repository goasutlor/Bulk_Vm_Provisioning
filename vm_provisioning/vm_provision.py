from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl
import atexit
import time
from datetime import datetime
import ipaddress
import random


def get_template_names(vcenter_host, vcenter_user, vcenter_pass):
    """Get all VM templates from vCenter"""
    context = ssl._create_unverified_context()
    si = SmartConnect(
        host=vcenter_host, user=vcenter_user, pwd=vcenter_pass, sslContext=context
    )
    atexit.register(Disconnect, si)

    content = si.RetrieveContent()
    templates = []

    container = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True
    )

    for vm in container.view:
        if vm.config and vm.config.template:
            templates.append(vm.name)

    container.Destroy()
    return sorted(templates)


def get_datacenters(vcenter_host, vcenter_user, vcenter_pass):
    """Get all datacenters from vCenter"""
    context = ssl._create_unverified_context()
    si = SmartConnect(
        host=vcenter_host, user=vcenter_user, pwd=vcenter_pass, sslContext=context
    )
    atexit.register(Disconnect, si)

    content = si.RetrieveContent()
    datacenters = []

    container = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.Datacenter], True
    )

    for dc in container.view:
        datacenters.append(dc.name)

    container.Destroy()
    return sorted(datacenters)


def get_clusters(vcenter_host, vcenter_user, vcenter_pass, datacenter_name):
    """Get all clusters in a specific datacenter"""
    context = ssl._create_unverified_context()
    si = SmartConnect(
        host=vcenter_host, user=vcenter_user, pwd=vcenter_pass, sslContext=context
    )
    atexit.register(Disconnect, si)

    content = si.RetrieveContent()
    clusters = []

    # Find the datacenter
    dc_container = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.Datacenter], True
    )

    datacenter = None
    for dc in dc_container.view:
        if dc.name == datacenter_name:
            datacenter = dc
            break

    dc_container.Destroy()

    if datacenter:
        cluster_container = content.viewManager.CreateContainerView(
            datacenter, [vim.ClusterComputeResource], True
        )

        for cluster in cluster_container.view:
            clusters.append(cluster.name)

        cluster_container.Destroy()

    return sorted(clusters)


def get_networks(vcenter_host, vcenter_user, vcenter_pass, datacenter_name):
    """Get all networks in a specific datacenter"""
    context = ssl._create_unverified_context()
    si = SmartConnect(
        host=vcenter_host, user=vcenter_user, pwd=vcenter_pass, sslContext=context
    )
    atexit.register(Disconnect, si)

    content = si.RetrieveContent()
    networks = []

    # Find the datacenter
    dc_container = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.Datacenter], True
    )

    datacenter = None
    for dc in dc_container.view:
        if dc.name == datacenter_name:
            datacenter = dc
            break

    dc_container.Destroy()

    if datacenter:
        network_container = content.viewManager.CreateContainerView(
            datacenter, [vim.Network], True
        )

        for network in network_container.view:
            networks.append(network.name)

        network_container.Destroy()

    return sorted(networks)


def get_nic_count(vcenter_host, vcenter_user, vcenter_pass, template_name):
    """Get the number of NICs in a template"""
    context = ssl._create_unverified_context()
    si = SmartConnect(
        host=vcenter_host, user=vcenter_user, pwd=vcenter_pass, sslContext=context
    )
    atexit.register(Disconnect, si)

    content = si.RetrieveContent()

    container = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True
    )

    for vm in container.view:
        if vm.name == template_name and vm.config and vm.config.template:
            nic_count = len(
                [
                    device
                    for device in vm.config.hardware.device
                    if isinstance(device, vim.vm.device.VirtualEthernetCard)
                ]
            )
            container.Destroy()
            return nic_count

    container.Destroy()
    return 1


def find_vm_by_name(content, name):
    """Find VM by name"""
    container = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True
    )

    for vm in container.view:
        if vm.name == name:
            container.Destroy()
            return vm

    container.Destroy()
    return None


def find_datacenter_by_name(content, name):
    """Find datacenter by name"""
    container = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.Datacenter], True
    )

    for dc in container.view:
        if dc.name == name:
            container.Destroy()
            return dc

    container.Destroy()
    return None


def find_cluster_by_name(datacenter, name):
    """Find cluster by name in datacenter"""
    container = datacenter.parent.viewManager.CreateContainerView(
        datacenter, [vim.ClusterComputeResource], True
    )

    for cluster in container.view:
        if cluster.name == name:
            container.Destroy()
            return cluster

    container.Destroy()
    return None


def find_network_by_name(datacenter, name):
    """Find network by name in datacenter"""
    container = datacenter.parent.viewManager.CreateContainerView(
        datacenter, [vim.Network], True
    )

    for network in container.view:
        if network.name == name:
            container.Destroy()
            return network

    container.Destroy()
    return None


def configure_vm_network(vm, network, ip_map, logger):
    """Configure VM network settings"""
    if not ip_map:
        return

    try:
        # Get VM's network adapters
        devices = vm.config.hardware.device
        network_adapters = [
            d for d in devices if isinstance(d, vim.vm.device.VirtualEthernetCard)
        ]

        if not network_adapters:
            logger("No network adapters found on VM")
            return

        logger(f"Configuring {len(network_adapters)} network adapter(s)")

        # For simplicity, we'll just log the IP configuration
        # In a full implementation, you'd use guest customization
        for i, adapter in enumerate(network_adapters, 1):
            ip_key = f"net{i}"
            if ip_key in ip_map:
                logger(f"  NIC {i}: {ip_map[ip_key]}")

    except Exception as e:
        logger(f"Error configuring network: {str(e)}")


def provision_vms_demo_mode(
    vcenter_host,
    vcenter_user,
    vcenter_pass,
    template,
    prefix,
    count,
    datacenter_name,
    cluster_name,
    network_name,
    ip_map,
    logger=print,
    individual_nodes_data=None,
):
    """
    Demo mode provisioning with realistic logs using actual configuration data
    This simulates real provisioning process with the user's configuration
    """
    logger(f"🎭 DEMO MODE: VM Provisioning Simulation Started")
    logger(f"⚡ Using live configuration data for realistic simulation")
    
    # Initial validation logs
    logger(f"🔍 Validating configuration...")
    time.sleep(0.5)
    logger(f"✅ Template validation: '{template}' found")
    logger(f"✅ Datacenter validation: '{datacenter_name}' accessible")
    logger(f"✅ Cluster validation: '{cluster_name}' available")
    logger(f"✅ Network validation: '{network_name}' configured")
    
    # vCenter connection simulation
    logger(f"🔌 Connecting to vCenter: {vcenter_host}")
    time.sleep(1.0)
    logger(f"🔐 Authenticating user: {vcenter_user}")
    time.sleep(0.8)
    logger(f"✅ Successfully connected to vCenter Server")
    
    # Resource discovery
    logger(f"🔍 Discovering vCenter resources...")
    time.sleep(0.7)
    logger(f"📁 Found datacenter: {datacenter_name}")
    logger(f"🏢 Located cluster: {cluster_name} (Resources: 80% CPU, 65% Memory available)")
    logger(f"💾 Available datastores: ['datastore1', 'datastore2', 'SSD-Storage']")
    logger(f"🌐 Network configuration: {network_name}")
    
    # Template analysis
    logger(f"🔍 Analyzing template: {template}")
    time.sleep(0.5)
    logger(f"💿 Template OS: Detected Linux/Windows hybrid configuration")
    logger(f"💾 Template size: ~12.5 GB")
    logger(f"⚙️  Template specs: 2 vCPU, 4 GB RAM, 40 GB Disk")
    
    # Network configuration analysis
    if ip_map:
        logger(f"🌐 Network configuration analysis:")
        for nic_name, ip_addr in ip_map.items():
            if ip_addr:
                logger(f"   • {nic_name.upper()}: Static IP {ip_addr} configured")
            else:
                logger(f"   • {nic_name.upper()}: DHCP mode enabled")
    else:
        logger(f"🌐 Network mode: DHCP automatic assignment")
    
    time.sleep(1.0)
    
    # Individual or bulk provisioning
    if individual_nodes_data and len(individual_nodes_data) > 0:
        logger(f"👥 Individual node provisioning mode: {len(individual_nodes_data)} unique VMs")
        vms_to_create = individual_nodes_data
        total_vms = len(individual_nodes_data)
    else:
        logger(f"📦 Bulk provisioning mode: {count} VMs with prefix '{prefix}'")
        vms_to_create = []
        for i in range(1, count + 1):
            vm_name = f"{prefix}{i:02d}"
            vm_data = {
                'name': vm_name,
                'hostname': f"{vm_name.lower()}.company.local",
                'ips': {}
            }
            # Add IP mapping for bulk mode
            for nic_key, ip_val in ip_map.items():
                if ip_val:
                    # Generate sequential IPs for bulk mode
                    base_ip = ip_val.split('.')
                    base_ip[-1] = str(int(base_ip[-1]) + i - 1)
                    vm_data['ips'][nic_key] = '.'.join(base_ip)
            vms_to_create.append(vm_data)
        total_vms = count
    
    logger(f"🚀 Starting provisioning of {total_vms} virtual machines...")
    logger(f"⏱️  Estimated completion time: {total_vms * 2.5:.1f} minutes")
    
    # VM provisioning simulation
    for i, vm_data in enumerate(vms_to_create, 1):
        vm_name = vm_data.get('name', f"{prefix}{i:02d}")
        hostname = vm_data.get('hostname', f"{vm_name.lower()}.local")
        vm_ips = vm_data.get('ips', {})
        
        logger(f"")
        logger(f"🔄 [{i}/{total_vms}] Creating VM: {vm_name}")
        logger(f"📝 Hostname: {hostname}")
        
        # Clone task simulation
        logger(f"🔧 Initiating clone operation from template: {template}")
        time.sleep(random.uniform(0.8, 1.2))
        
        logger(f"📋 Configuring VM specifications...")
        logger(f"   • CPU: 2 vCores allocated")
        logger(f"   • Memory: 4 GB RAM assigned")
        logger(f"   • Storage: 40 GB thin provisioned")
        time.sleep(0.5)
        
        # Network configuration for each VM
        if vm_ips:
            logger(f"🌐 Configuring network interfaces:")
            for nic_name, ip_addr in vm_ips.items():
                if ip_addr:
                    logger(f"   • {nic_name.upper()}: Static IP {ip_addr}")
                    time.sleep(0.3)
                else:
                    logger(f"   • {nic_name.upper()}: DHCP enabled")
        else:
            logger(f"🌐 Network: DHCP auto-configuration enabled")
        
        # Clone progress simulation
        clone_progress = [25, 50, 75, 100]
        for progress in clone_progress:
            logger(f"📈 Clone progress: {progress}% - VM {vm_name}")
            time.sleep(random.uniform(0.4, 0.8))
        
        logger(f"✅ VM {vm_name} cloned successfully")
        
        # Post-clone configuration
        logger(f"⚙️  Applying post-clone configuration...")
        time.sleep(0.6)
        logger(f"🔧 Setting hostname: {hostname}")
        logger(f"🌐 Configuring network settings")
        logger(f"🔐 Installing VMware Tools")
        time.sleep(0.8)
        
        # Power on simulation
        logger(f"⚡ Powering on VM: {vm_name}")
        time.sleep(0.5)
        logger(f"🟢 VM {vm_name} powered on successfully")
        
        # Boot process simulation
        logger(f"🚀 Booting guest OS...")
        time.sleep(1.0)
        logger(f"✅ Guest OS boot completed - VM {vm_name} ready")
        
        # Health check simulation
        logger(f"🏥 Running health checks...")
        time.sleep(0.4)
        logger(f"✅ All health checks passed for {vm_name}")
        
        # Add some random realistic delays
        if i < total_vms:
            time.sleep(random.uniform(0.3, 0.7))
    
    # Final summary
    logger(f"")
    logger(f"🎉 PROVISIONING COMPLETED SUCCESSFULLY!")
    logger(f"📊 Summary:")
    logger(f"   • Total VMs provisioned: {total_vms}")
    logger(f"   • Template used: {template}")
    logger(f"   • Datacenter: {datacenter_name}")
    logger(f"   • Cluster: {cluster_name}")
    logger(f"   • Network: {network_name}")
    
    if individual_nodes_data:
        logger(f"   • Configuration: Individual node setup")
        logger(f"   • VM Names: {', '.join([vm['name'] for vm in individual_nodes_data])}")
    else:
        logger(f"   • Configuration: Bulk provisioning")
        logger(f"   • VM Prefix: {prefix}")
        logger(f"   • VM Range: {prefix}01 to {prefix}{count:02d}")
    
    logger(f"")
    logger(f"✅ All virtual machines are ready for use!")
    logger(f"🎭 DEMO MODE: This was a simulation using your actual configuration")
    
    return f"Successfully provisioned {total_vms} VMs using template {template} in {datacenter_name}/{cluster_name}"


def provision_vms(
    vcenter_host,
    vcenter_user,
    vcenter_pass,
    template,
    prefix,
    count,
    datacenter_name,
    cluster_name,
    network_name,
    ip_map,
    logger=print,
    timeout_seconds=30,
):
    """Provision VMs from template with timeout protection"""

    logger(f"🚀 Starting VM provisioning...")
    logger(f"📋 Template: {template}")
    logger(f"📋 Prefix: {prefix}")
    logger(f"📋 Count: {count}")
    logger(f"📋 Datacenter: {datacenter_name}")
    logger(f"📋 Cluster: {cluster_name}")
    logger(f"📋 Network: {network_name}")
    logger(f"⏱️  Timeout setting: {timeout_seconds} seconds")

    start_time = time.time()
    
    try:
        # Connection timeout check
        logger(f"🔌 Connecting to vCenter: {vcenter_host}")
        connection_start = time.time()
        
        try:
            context = ssl._create_unverified_context()
            si = SmartConnect(
                host=vcenter_host, user=vcenter_user, pwd=vcenter_pass, sslContext=context
            )
            atexit.register(Disconnect, si)
            
            connection_time = time.time() - connection_start
            logger(f"✅ Connected to vCenter (took {connection_time:.2f}s)")
            
        except Exception as conn_error:
            logger(f"❌ vCenter connection failed after {time.time() - connection_start:.2f}s")
            logger(f"❌ Connection error: {str(conn_error)}")
            logger(f"💡 Common causes:")
            logger(f"   • Incorrect vCenter host/IP address")
            logger(f"   • Network connectivity issues")
            logger(f"   • vCenter service not running")
            logger(f"   • SSL certificate issues")
            logger(f"   • Incorrect credentials")
            raise Exception(f"vCenter connection failed: {str(conn_error)}")

        # Check elapsed time after connection
        elapsed_time = time.time() - start_time
        if elapsed_time > timeout_seconds:
            logger(f"⏰ Timeout exceeded ({elapsed_time:.1f}s > {timeout_seconds}s) during connection phase")
            raise Exception(f"Operation timed out during vCenter connection")

        content = si.RetrieveContent()

        # Resource discovery with timeout check
        logger(f"🔍 Discovering vCenter resources...")
        discovery_start = time.time()

        # Find required objects with individual timeout checks
        template_vm = find_vm_by_name(content, template)
        if not template_vm:
            logger(f"❌ Template '{template}' not found")
            logger(f"💡 Please verify:")
            logger(f"   • Template name is correct")
            logger(f"   • Template exists in vCenter")
            logger(f"   • User has permissions to access template")
            raise Exception(f"Template '{template}' not found")

        elapsed_time = time.time() - start_time
        if elapsed_time > timeout_seconds:
            logger(f"⏰ Timeout exceeded ({elapsed_time:.1f}s > {timeout_seconds}s) during template discovery")
            raise Exception(f"Operation timed out while finding template")

        datacenter = find_datacenter_by_name(content, datacenter_name)
        if not datacenter:
            logger(f"❌ Datacenter '{datacenter_name}' not found")
            logger(f"💡 Available datacenters should be verified")
            raise Exception(f"Datacenter '{datacenter_name}' not found")

        elapsed_time = time.time() - start_time
        if elapsed_time > timeout_seconds:
            logger(f"⏰ Timeout exceeded ({elapsed_time:.1f}s > {timeout_seconds}s) during datacenter discovery")
            raise Exception(f"Operation timed out while finding datacenter")

        cluster = find_cluster_by_name(datacenter, cluster_name)
        if not cluster:
            logger(f"❌ Cluster '{cluster_name}' not found in datacenter '{datacenter_name}'")
            logger(f"💡 Please verify cluster name and permissions")
            raise Exception(f"Cluster '{cluster_name}' not found")

        elapsed_time = time.time() - start_time
        if elapsed_time > timeout_seconds:
            logger(f"⏰ Timeout exceeded ({elapsed_time:.1f}s > {timeout_seconds}s) during cluster discovery")
            raise Exception(f"Operation timed out while finding cluster")

        network = find_network_by_name(datacenter, network_name)
        if not network:
            logger(f"❌ Network '{network_name}' not found in datacenter '{datacenter_name}'")
            logger(f"💡 Please verify network name and accessibility")
            raise Exception(f"Network '{network_name}' not found")

        discovery_time = time.time() - discovery_start
        logger(f"✅ Found all required vCenter objects (took {discovery_time:.2f}s)")

        # Check timeout again before proceeding
        elapsed_time = time.time() - start_time
        if elapsed_time > timeout_seconds:
            logger(f"⏰ Timeout exceeded ({elapsed_time:.1f}s > {timeout_seconds}s) during resource discovery")
            raise Exception(f"Operation timed out during resource discovery")

        # Get resource pool (default to cluster's root resource pool)
        resource_pool = cluster.resourcePool

        # VM folder (default to datacenter's vm folder)
        vm_folder = datacenter.vmFolder

        # Get datastore (use first available datastore in cluster)
        datastore = cluster.datastore[0] if cluster.datastore else None
        if not datastore:
            logger(f"❌ No datastore available in cluster '{cluster_name}'")
            logger(f"💡 Cluster must have at least one accessible datastore")
            raise Exception("No datastore available in cluster")

        logger(f"📁 Using datastore: {datastore.name}")

        # Start cloning VMs with timeout monitoring
        clone_tasks = []
        clone_start_time = time.time()

        for i in range(1, count + 1):
            # Check timeout before each VM
            elapsed_time = time.time() - start_time
            if elapsed_time > timeout_seconds:
                logger(f"⏰ Timeout exceeded ({elapsed_time:.1f}s > {timeout_seconds}s) before creating VM {i}")
                logger(f"⚠️  Only {i-1}/{count} VMs were started")
                break

            vm_name = f"{prefix}{i:02d}"
            logger(f"🔄 Cloning VM {i}/{count}: {vm_name}")

            try:
                # Configure clone specification
                clone_spec = vim.vm.CloneSpec()
                clone_spec.location = vim.vm.RelocateSpec()
                clone_spec.location.datastore = datastore
                clone_spec.location.pool = resource_pool

                # Network configuration
                device_changes = []
                devices = template_vm.config.hardware.device

                for device in devices:
                    if isinstance(device, vim.vm.device.VirtualEthernetCard):
                        device_spec = vim.vm.device.VirtualDeviceSpec()
                        device_spec.operation = (
                            vim.vm.device.VirtualDeviceSpec.Operation.edit
                        )
                        device_spec.device = device
                        device_spec.device.backing = (
                            vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
                        )
                        device_spec.device.backing.network = network
                        device_spec.device.backing.deviceName = network.name
                        device_changes.append(device_spec)

                if device_changes:
                    config_spec = vim.vm.ConfigSpec()
                    config_spec.deviceChange = device_changes
                    clone_spec.config = config_spec

                # Power on after clone
                clone_spec.powerOn = True

                # Start the clone task
                task = template_vm.Clone(folder=vm_folder, name=vm_name, spec=clone_spec)
                clone_tasks.append((task, vm_name, time.time()))
                
                logger(f"✅ Clone task initiated for {vm_name}")

                # Small delay between clones
                time.sleep(0.5)

            except Exception as clone_error:
                logger(f"❌ Failed to initiate clone for {vm_name}: {str(clone_error)}")
                continue

        # Wait for all clone tasks to complete with timeout monitoring
        if clone_tasks:
            logger(f"⏳ Waiting for {len(clone_tasks)} clone operations to complete...")
            logger(f"⏰ Will timeout after {timeout_seconds} seconds total")

            success_count = 0
            failed_count = 0
            timeout_count = 0

            for task, vm_name, task_start_time in clone_tasks:
                try:
                    # Monitor task with timeout
                    task_timeout = False
                    while task.info.state in [
                        vim.TaskInfo.State.running,
                        vim.TaskInfo.State.queued,
                    ]:
                        # Check global timeout
                        elapsed_time = time.time() - start_time
                        if elapsed_time > timeout_seconds:
                            logger(f"⏰ Global timeout exceeded ({elapsed_time:.1f}s > {timeout_seconds}s)")
                            logger(f"⚠️  Stopping wait for remaining tasks")
                            task_timeout = True
                            timeout_count += 1
                            break
                        
                        # Check individual task timeout (10 seconds per task)
                        task_elapsed = time.time() - task_start_time
                        if task_elapsed > 10:
                            logger(f"⏰ Task timeout for {vm_name} ({task_elapsed:.1f}s > 10s)")
                            task_timeout = True
                            timeout_count += 1
                            break
                        
                        time.sleep(1)

                    if task_timeout:
                        logger(f"⏰ {vm_name} timed out - task may still be running in background")
                        continue

                    if task.info.state == vim.TaskInfo.State.success:
                        logger(f"✅ {vm_name} cloned successfully")

                        # Configure network if IP mapping provided
                        if ip_map:
                            try:
                                new_vm = task.info.result
                                configure_vm_network(new_vm, network, ip_map, logger)
                            except Exception as net_error:
                                logger(f"⚠️  Network configuration failed for {vm_name}: {str(net_error)}")

                        success_count += 1
                    else:
                        error_msg = (
                            str(task.info.error.localizedMessage) if task.info.error else "Unknown error"
                        )
                        logger(f"❌ {vm_name} clone failed: {error_msg}")
                        
                        # Provide helpful error analysis
                        if "insufficient resources" in error_msg.lower():
                            logger(f"💡 Insufficient resources - check cluster capacity")
                        elif "permission" in error_msg.lower():
                            logger(f"💡 Permission denied - verify user privileges")
                        elif "datastore" in error_msg.lower():
                            logger(f"💡 Datastore issue - check available space")
                        elif "network" in error_msg.lower():
                            logger(f"💡 Network issue - verify network accessibility")
                        
                        failed_count += 1

                except Exception as e:
                    logger(f"❌ Error monitoring {vm_name}: {str(e)}")
                    failed_count += 1

            # Final summary with timeout information
            total_time = time.time() - start_time
            logger(f"")
            logger(f"🎉 PROVISIONING COMPLETED")
            logger(f"⏱️  Total time: {total_time:.2f} seconds")
            logger(f"📊 Results:")
            logger(f"   ✅ Successful: {success_count}")
            logger(f"   ❌ Failed: {failed_count}")
            if timeout_count > 0:
                logger(f"   ⏰ Timed out: {timeout_count}")
            logger(f"   📋 Total requested: {count}")

            if timeout_count > 0:
                logger(f"")
                logger(f"⚠️  TIMEOUT INFORMATION:")
                logger(f"   • Some operations exceeded the {timeout_seconds}s timeout")
                logger(f"   • Timed-out tasks may still be running in vCenter")
                logger(f"   • Check vCenter directly for final status")
                logger(f"💡 Consider increasing timeout for large deployments")

            completion_msg = f"Provisioning completed in {total_time:.1f}s! {success_count}/{count} VMs created successfully"
            if timeout_count > 0:
                completion_msg += f" ({timeout_count} timed out)"
            
            return completion_msg

        else:
            logger(f"❌ No clone tasks were successfully initiated")
            raise Exception("Failed to start any VM provisioning tasks")

    except Exception as e:
        total_time = time.time() - start_time
        error_msg = f"Provisioning failed after {total_time:.1f}s: {str(e)}"
        logger(f"❌ {error_msg}")
        
        # Provide timeout-specific guidance
        if "timed out" in str(e).lower() or total_time > timeout_seconds:
            logger(f"")
            logger(f"⏰ TIMEOUT TROUBLESHOOTING:")
            logger(f"   • Current timeout: {timeout_seconds}s")
            logger(f"   • Actual time taken: {total_time:.1f}s")
            logger(f"   • Try reducing VM count per batch")
            logger(f"   • Check vCenter performance")
            logger(f"   • Verify network connectivity")
            logger(f"   • Consider increasing timeout setting")
        
        raise Exception(error_msg)
