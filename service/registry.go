package service

import (
	"fmt"
	"sync"
	"time"
	"code.google.com/p/go-uuid/uuid"
)

type ServiceRegistry struct {
	services map[uuid.UUID]*Service
	regMu    *sync.Mutex
}

func NewServiceRegistry() *ServiceRegistry {
	registry := &ServiceRegistry{}
	registry.regMu = &sync.Mutex{}
	registry.services = make(map[string]*Service)
	return registry
}

func (self *ServiceRegistry) RegisterService(srv *Service) {
	self.regMu.Lock()
	defer self.regMu.Unlock()
	if _, ok := self.services[srv.UUID]; ok {
		log.Info("[service] Service `%s` already registered", srv.Name)
		srv, _ = self.services[srv.Name]
		srv.Online = ServiceOnline
		return
	}
	self.services[srv.Name] = srv
}

func (self *ServiceRegistry) GetServiceByName(name string) *Service {
	if srv, ok := self.services[name]; ok {
		return srv
	}
	return nil
}

type Service struct {
	Name           string
	UUID           uuid.UUID
	Version        string
	Online         bool
	LastPing       time.Time
	LastPong       time.Time
	RespondedCount int
}

func NewService() *Service {
	service := &Service{}
	return service
}

func (self *Service) String() string {
	online := "offline"
	if self.Online {
		online = "online"
	}
	return fmt.Sprintf(self.Name, online)
}
