describe('DIP upload', () => {
  it('Creates and deletes a folder', () => {
    // Generate folder identifier with a minor unpredictability
    const identifier = 'e2e_test_folder_' + 
      Math.random().toString(36).substring(7);

    cy.visit('/login')
    cy.get('input[name=username]').type(Cypress.env('username'))
    cy.get('input[name=password]').type(Cypress.env('password'))
    cy.get('.main form').submit()

    cy.visit('/new_folder')
    cy.get('input[name=identifier]').type(identifier)
    cy.get('input[name=objectszip]').attachFile('dips/test_a.zip')
    cy.get('.main form').submit()

    cy.contains('A background process has been launched')
    cy.wait(2000)

    cy.reload()
    cy.get('.main input[name=query]').type(identifier)
      .closest('form').submit()

    cy.get('.main table').contains(identifier).closest('tr')
      .contains('See more').click()

    cy.contains('Showing 10 results')
    cy.contains('Delete').click()
  
    cy.get('input[name=identifier]').type(identifier)
    cy.get('.main form').submit()

    cy.visit('/orphan_folders')
    cy.get('.main input[name=query]').type(identifier)
      .closest('form').submit()

    cy.get('.main table').contains(identifier).should('not.exist')
  })
})
